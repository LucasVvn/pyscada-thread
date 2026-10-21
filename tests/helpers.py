# -*- coding: utf-8 -*-
"""Outils communs aux tests : nœud CoAP simulé et objets PyScada."""
import asyncio
import socket
import threading
from unittest import mock

from pyscada.models import Device, DeviceProtocol, Unit, Variable
from pyscada.thread import PROTOCOL_ID
from pyscada.thread.models import ThreadDevice, ThreadVariable
from pyscada.thread.simulator import build_site, start_server


def free_udp_port():
    with socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as s:
        s.bind(("::1", 0))
        return s.getsockname()[1]


class SimulatedNode:
    """Lance le nœud simulé dans un thread avec sa propre boucle asyncio."""

    def __init__(self, port=None, site=None):
        self.port = port or free_udp_port()
        self.site = site or build_site(noise=0)
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.context = None

    def start(self):
        self.thread.start()
        self.context = asyncio.run_coroutine_threadsafe(
            start_server("::1", self.port, self.site), self.loop
        ).result(5)
        return self

    def stop(self):
        asyncio.run_coroutine_threadsafe(self.context.shutdown(), self.loop).result(5)
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(5)


def make_device(port, timeout=2.0, retries=0, **kwargs):
    protocol = DeviceProtocol.objects.get(pk=PROTOCOL_ID)
    device = Device.objects.create(
        short_name="noeud-test", protocol=protocol, polling_interval=5, active=True
    )
    ThreadDevice.objects.create(
        thread_device=device,
        ipv6_address="::1",
        port=port,
        timeout=timeout,
        retries=retries,
        **kwargs,
    )
    return device


def make_variable(device, name, resource, payload_format=0, json_key=None, **kwargs):
    unit, _ = Unit.objects.get_or_create(unit="°C", defaults={"description": "°C"})
    variable = Variable.objects.create(
        name=name, device=device, unit=unit, active=True, **kwargs
    )
    ThreadVariable.objects.create(
        thread_variable=variable,
        resource=resource,
        payload_format=payload_format,
        json_key=json_key,
    )
    return variable


def device_instance(device):
    """Instancie pyscada.thread.device.Device sans l'attente de 5 s du cœur."""
    from pyscada.thread.device import Device as ThreadDeviceClass

    with mock.patch("pyscada.device.sleep"):
        return ThreadDeviceClass(Device.objects.get(pk=device.pk))
