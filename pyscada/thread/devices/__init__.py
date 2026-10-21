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
from pyscada.device import GenericHandlerDevice

import logging

logger = logging.getLogger(__name__)


class GenericDevice(GenericHandlerDevice):
    """
    Handler Thread : lit les ressources CoAP du nœud.
    """

    def __init__(self, pyscada_device, variables):
        super().__init__(pyscada_device, variables)
        self.driver_ok = driver_ok
        self._protocol = PROTOCOL_ID
        self.coap = None

    def connect(self):
        if super().connect() == False:
            return False
        # CoAP est sans connexion : « connecté » veut dire que le client est prêt.
        if self.coap is None:
            self.coap = get_runner()
        self.inst = self.coap
        return True

    def before_read(self):
        if not super().before_read():
            return False
        self.accessibility()
        return True

    def disconnect(self):
        # le client CoAP reste ouvert entre deux lectures
        self.inst = None
        return True

    def uri(self, variable_instance):
        td = self._device.threaddevice
        tv = variable_instance.threadvariable
        return td.base_uri() + tv.path()

    def read_data(self, variable_instance):
        tv = variable_instance.threadvariable
        td = self._device.threaddevice
        uri = self.uri(variable_instance)
        try:
            response = self.coap.get(uri, td.timeout)
        except CoapResponseError as e:
            logger.warning(f"{self._device} - GET {e}")
            return None
        except Exception as e:
            logger.info(f"{self._device} - GET {uri} failed : {e!r}")
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
        td = self._device.threaddevice
        uri = self.uri(variable)
        payload = format_payload(value, tv.payload_format, tv.json_key)
        try:
            self.coap.put(uri, payload, td.timeout)
        except CoapResponseError as e:
            logger.warning(f"{self._device} - PUT {payload!r} refused : {e}")
            return None
        except Exception as e:
            logger.info(f"{self._device} - PUT {uri} {payload!r} failed : {e!r}")
            return None
        return value
