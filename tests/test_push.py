# -*- coding: utf-8 -*-
"""Mode push : le nœud envoie, PyScada enregistre à réception."""
import asyncio

import aiocoap
from django.test import TestCase


from .helpers import device_instance, free_udp_port, make_device, make_variable


def push(port, path, payload, method=aiocoap.POST):
    """Envoi depuis un « capteur » (client CoAP sur ::1)."""

    async def send():
        context = await aiocoap.Context.create_client_context()
        try:
            message = aiocoap.Message(
                code=method, uri=f"coap://[::1]:{port}{path}", payload=payload
            )
            return await asyncio.wait_for(context.request(message).response, 5)
        finally:
            await context.shutdown()

    return asyncio.run(send())


class PushModeTest(TestCase):
    def make_push_device(self, address="::1"):
        port = free_udp_port()
        device = make_device(port=5683, mode=1, listen_port=port)
        device.threaddevice.ipv6_address = address
        device.threaddevice.save()
        return device, port

    def tearDown(self):
        if getattr(self, "dev", None) is not None and self.dev._h.listener:
            self.dev._h.listener.stop()

    def test_push_is_recorded_on_next_cycle(self):
        device, port = self.make_push_device()
        make_variable(device, "temperature", "/temperature")
        make_variable(device, "co2", "/mesures", payload_format=1, json_key="co2")
        self.dev = device_instance(device)
        self.assertEqual(self.dev.request_data(), [])  # démarre l'écoute

        r1 = push(port, "/temperature", b"22.5")
        r2 = push(port, "/mesures", b'{"co2": 640}', method=aiocoap.PUT)
        self.assertEqual(r1.code, aiocoap.CHANGED)
        self.assertEqual(r2.code, aiocoap.CHANGED)

        updated = self.dev.request_data()
        self.assertEqual({v.name: v.value for v in updated}, {"temperature": 22.5, "co2": 640})
        self.assertEqual(self.dev.request_data(), [])

    def test_push_from_other_address_is_refused(self):
        device, port = self.make_push_device(address="fd12::a1")
        make_variable(device, "temperature", "/temperature")
        self.dev = device_instance(device)
        self.dev.request_data()

        with self.assertLogs("pyscada.thread.push", "WARNING"):
            response = push(port, "/temperature", b"22.5")

        self.assertEqual(response.code, aiocoap.FORBIDDEN)
        self.assertEqual(self.dev.request_data(), [])

    def test_unreadable_push_is_bad_request(self):
        device, port = self.make_push_device()
        make_variable(device, "temperature", "/temperature")
        self.dev = device_instance(device)
        self.dev.request_data()

        with self.assertLogs("pyscada.thread.push", "WARNING"):
            response = push(port, "/temperature", b"chaud")

        self.assertEqual(response.code, aiocoap.BAD_REQUEST)
