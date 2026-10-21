# -*- coding: utf-8 -*-
"""
Mode push : le nœud envoie ses mesures (POST ou PUT) et PyScada les enregistre
à réception, au lieu de les demander à chaque intervalle.

Le serveur CoAP tourne dans la boucle asyncio du CoapRunner. Les valeurs reçues
attendent dans une file jusqu'au prochain passage du démon, qui les enregistre
avec l'heure de réception.
"""
from __future__ import unicode_literals

import ipaddress
import logging
import queue
from time import time_ns

from .coap import parse_payload

logger = logging.getLogger(__name__)

try:
    import aiocoap
    import aiocoap.resource as resource
except ImportError:
    resource = None


def same_address(a, b):
    try:
        return ipaddress.ip_address(a) == ipaddress.ip_address(b)
    except ValueError:
        return False


def remote_host(request):
    """Adresse IPv6 de l'expéditeur, sans port ni crochets."""
    try:
        return request.remote.sockaddr[0].split("%")[0]
    except Exception:
        host = request.remote.hostinfo
        if host.startswith("["):
            host = host[1 : host.index("]")]
        return host


class PushResource(resource.Resource if resource else object):
    """Ressource d'une variable : reçoit la valeur poussée par le nœud."""

    def __init__(self, listener, variable_id, payload_format, json_key):
        super().__init__()
        self.listener = listener
        self.variable_id = variable_id
        self.payload_format = payload_format
        self.json_key = json_key

    async def render_post(self, request):
        return self.listener.receive(self, request)

    async def render_put(self, request):
        return self.listener.receive(self, request)


class PushListener:
    """Écoute les envois d'un nœud Thread sur listen_port."""

    def __init__(self, runner, device, variables):
        self.runner = runner
        self.device = device
        self.node_address = device.threaddevice.ipv6_address
        self.received = queue.Queue()
        self.last_message = None
        self.started = None
        self.site = resource.Site()
        self.paths = {}
        for variable in variables.values():
            tv = variable.threadvariable
            path = tuple(p for p in tv.path().split("/") if p)
            self.paths[path] = variable.pk
            self.site.add_resource(
                path,
                PushResource(self, variable.pk, tv.payload_format, tv.json_key),
            )
        self.context = None

    def start(self):
        port = self.device.threaddevice.listen_port
        self.context = self.runner.start_server(self.site, ("::", port))
        self.started = time_ns() / 1000000000
        logger.info(f"{self.device} - listening for CoAP pushes on UDP port {port}")

    def stop(self):
        if self.context is not None:
            self.runner.stop_server(self.context)
            self.context = None

    def receive(self, res, request):
        sender = remote_host(request)
        if not same_address(sender, self.node_address):
            logger.warning(
                f"{self.device} - push from {sender} refused, {self.node_address} expected"
            )
            return aiocoap.Message(code=aiocoap.FORBIDDEN)
        try:
            value = parse_payload(request.payload, res.payload_format, res.json_key)
        except (ValueError, KeyError, IndexError, TypeError) as e:
            logger.warning(
                f"{self.device} - unreadable push {request.payload!r} : {e}"
            )
            return aiocoap.Message(code=aiocoap.BAD_REQUEST)
        timestamp = time_ns() / 1000000000
        self.last_message = timestamp
        self.received.put((res.variable_id, value, timestamp))
        return aiocoap.Message(code=aiocoap.CHANGED)

    def silent_for(self, now=None):
        """Secondes écoulées depuis le dernier envoi (ou le démarrage de l'écoute)."""
        if now is None:
            now = time_ns() / 1000000000
        last = self.last_message if self.last_message is not None else self.started
        return now - last

    def drain(self):
        """Renvoie et vide la liste des (variable_id, valeur, horodatage) reçus."""
        items = []
        while True:
            try:
                items.append(self.received.get_nowait())
            except queue.Empty:
                return items
