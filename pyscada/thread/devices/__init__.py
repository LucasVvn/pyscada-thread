# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from .. import PROTOCOL_ID
from ..coap import (
    driver_ok,
    get_runner,
    parse_payload,
    format_payload,
    CoapResponseError,
)
from ..push import PushListener
from pyscada.device import GenericHandlerDevice

import logging

logger = logging.getLogger(__name__)


class NodeUnreachable(Exception):
    """Aucune réponse du nœud après toutes les tentatives."""


class GenericDevice(GenericHandlerDevice):
    """
    Handler Thread : lit les ressources CoAP du nœud.
    """

    def __init__(self, pyscada_device, variables):
        super().__init__(pyscada_device, variables)
        self.driver_ok = driver_ok
        self._protocol = PROTOCOL_ID
        self.coap = None
        # vrai dès qu'une requête du cycle en cours est restée sans réponse
        self._unreachable = False
        self.listener = None
        self._silent = False

    def connect(self):
        if super().connect() == False:
            return False
        # CoAP est sans connexion : « connecté » veut dire que le client est prêt.
        if self.coap is None:
            self.coap = get_runner()
        self.inst = self.coap
        if self._device.threaddevice.is_push() and self.listener is None:
            listener = PushListener(self.coap, self._device, self._variables)
            try:
                listener.start()
            except OSError as e:
                self._not_accessible_reason = f"cannot listen for pushes : {e}"
                self.inst = None
                return False
            self.listener = listener
        return True

    def read_data_all(self, variables_dict, erase_cache=False):
        if not self._device.threaddevice.is_push():
            return super().read_data_all(variables_dict, erase_cache)
        # Mode push : on enregistre ce que le nœud a envoyé depuis le dernier passage.
        output = []
        if self.before_read():
            for variable_id, value, timestamp in self.listener.drain():
                item = variables_dict.get(variable_id)
                if item is None or not item.readable:
                    continue
                if item.update_values([value], [timestamp], erase_cache=erase_cache):
                    if item not in output:
                        output.append(item)
            self.check_heartbeat()
        self.after_read()
        return output

    def check_heartbeat(self):
        """
        Capteur muet : aucun envoi depuis heartbeat_timeout secondes.
        Alerte une seule fois, et un message quand le nœud se manifeste à nouveau.
        """
        limit = self._device.threaddevice.heartbeat_timeout
        if not limit:
            return
        silent_for = self.listener.silent_for()
        if silent_for > limit:
            self._unreachable = True
            self._not_accessible_reason = (
                f"silent node, no push for {silent_for:.0f} s (limit {limit} s)"
            )
            if not self._silent:
                self._silent = True
                logger.warning(f"{self._device} - {self._not_accessible_reason}")
        elif self._silent:
            self._silent = False
            logger.info(f"{self._device} - node is sending again")

    def before_read(self):
        self._unreachable = False
        return super().before_read()

    def after_read(self):
        # Un seul message quand le nœud devient injoignable, un seul quand il revient.
        self.inst = None if self._unreachable else self.coap
        self.accessibility()
        return super().after_read()

    def disconnect(self):
        # le client CoAP reste ouvert entre deux lectures
        self.inst = None
        return True

    def uri(self, variable_instance):
        td = self._device.threaddevice
        tv = variable_instance.threadvariable
        return td.base_uri() + tv.path()

    def send(self, method, uri, *args):
        """
        Requête CoAP avec les tentatives du device. Une erreur CoAP (4.xx, 5.xx)
        n'est pas retentée : le nœud a répondu, il est donc joignable.
        """
        td = self._device.threaddevice
        attempts = td.retries + 1
        for attempt in range(1, attempts + 1):
            try:
                return getattr(self.coap, method)(uri, *args, td.timeout)
            except CoapResponseError:
                raise
            except Exception as e:
                error = e
                logger.debug(
                    f"{self._device} - {method.upper()} {uri} attempt {attempt}/{attempts} failed : {e!r}"
                )
        self._unreachable = True
        self._not_accessible_reason = (
            f"no CoAP response from {td.base_uri()} after {attempts} attempt(s), "
            f"timeout {td.timeout} s ({error!r})"
        )
        raise NodeUnreachable(self._not_accessible_reason)

    def read_data(self, variable_instance):
        if self._unreachable:
            # inutile d'attendre le délai pour chaque variable d'un nœud muet
            return None
        tv = variable_instance.threadvariable
        uri = self.uri(variable_instance)
        try:
            response = self.send("get", uri)
        except CoapResponseError as e:
            logger.warning(f"{self._device} - GET {e}")
            return None
        except NodeUnreachable:
            return None
        try:
            return parse_payload(response.payload, tv.payload_format, tv.json_key)
        except (ValueError, KeyError, IndexError, TypeError) as e:
            logger.warning(
                f"{self._device} - cannot read value from {uri} : {response.payload!r} ({e})"
            )
            return None

    def write_data(self, variable_id, value, task):
        """
        PUT de la valeur sur la ressource CoAP de la variable.
        Renvoie la valeur écrite si le nœud l'a acceptée, None sinon.
        """
        variable = self._variables.get(variable_id)
        if variable is None or not self.connect():
            return None
        tv = variable.threadvariable
        uri = self.uri(variable)
        payload = format_payload(value, tv.payload_format, tv.json_key)
        try:
            self.send("put", uri, payload)
        except CoapResponseError as e:
            logger.warning(f"{self._device} - PUT {payload!r} refused : {e}")
            return None
        except NodeUnreachable as e:
            logger.warning(f"{self._device} - PUT {uri} {payload!r} failed : {e}")
            return None
        return value
