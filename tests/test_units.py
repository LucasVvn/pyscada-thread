# -*- coding: utf-8 -*-
"""Tests unitaires : conversions, modèles, protocole, worker, admin."""
from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase

from pyscada.models import Device, DeviceProtocol
from pyscada.thread import PROTOCOL_ID, parent_process_list
from pyscada.thread.coap import format_payload, parse_payload
from pyscada.thread.push import same_address
from pyscada.thread.worker import Process

from .helpers import make_device, make_variable


class ParsePayloadTest(SimpleTestCase):
    def test_plain_text(self):
        self.assertEqual(parse_payload(b"21.4"), 21.4)
        self.assertEqual(parse_payload(b" 640\n"), 640)
        self.assertIs(parse_payload(b"on"), True)
        self.assertIs(parse_payload(b"false"), False)

    def test_json(self):
        payload = b'{"capteur": {"t": 21.4}, "liste": [5, 6]}'
        self.assertEqual(parse_payload(payload, 1, "capteur t"), 21.4)
        self.assertEqual(parse_payload(payload, 1, "liste [1]"), 6)
        self.assertEqual(parse_payload(b"12", 1), 12)

    def test_errors(self):
        with self.assertRaises(ValueError):
            parse_payload(b"chaud")
        with self.assertRaises(KeyError):
            parse_payload(b'{"a": 1}', 1, "b")


class FormatPayloadTest(SimpleTestCase):
    def test_plain_text(self):
        self.assertEqual(format_payload(True), b"1")
        self.assertEqual(format_payload(21.0), b"21")
        self.assertEqual(format_payload(21.5), b"21.5")

    def test_json(self):
        self.assertEqual(format_payload(1, 1, "relais"), b'{"relais": 1}')
        self.assertEqual(format_payload(1, 1, "a b"), b'{"a": {"b": 1}}')
        self.assertEqual(format_payload(2.5, 1), b"2.5")


class AddressTest(SimpleTestCase):
    def test_same_address(self):
        self.assertTrue(same_address("fd12::a1", "fd12:0:0:0:0:0:0:a1"))
        self.assertFalse(same_address("fd12::a1", "fd12::a2"))
        self.assertFalse(same_address("pas-une-ip", "fd12::a1"))


class ProtocolTest(TestCase):
    def test_protocol_registered(self):
        protocol = DeviceProtocol.objects.get(pk=PROTOCOL_ID)
        self.assertEqual(protocol.protocol, "thread")
        self.assertEqual(protocol.device_class, "pyscada.thread.device")
        self.assertEqual(parent_process_list[0]["pk"], PROTOCOL_ID)
        self.assertEqual(
            parent_process_list[0]["process_class"], "pyscada.thread.worker.Process"
        )

    def test_worker_filter_only_thread_devices(self):
        thread_device = make_device(5683)
        Device.objects.create(
            short_name="autre", protocol=DeviceProtocol.objects.get(pk=1)
        )
        found = Device.objects.filter(active=True, **Process.device_filter)
        self.assertEqual(list(found), [thread_device])


class ModelTest(TestCase):
    def test_uri(self):
        device = make_device(5683)
        device.threaddevice.ipv6_address = "fd12::a1"
        variable = make_variable(device, "temperature", "temperature/")
        self.assertEqual(device.threaddevice.base_uri(), "coap://[fd12::a1]:5683")
        self.assertEqual(variable.threadvariable.path(), "/temperature")
        self.assertFalse(device.threaddevice.is_push())


class AdminTest(TestCase):
    def test_pages(self):
        user = User.objects.create_superuser("admin", "a@example.org", "x")
        self.client.force_login(user)
        device = make_device(5683)
        make_variable(device, "temperature", "/temperature")
        for url in [
            "/admin/thread/extendedthreaddevice/",
            "/admin/thread/extendedthreaddevice/add/",
            f"/admin/thread/extendedthreaddevice/{device.pk}/change/",
            "/admin/thread/extendedthreadvariable/",
            "/admin/thread/extendedthreadvariable/add/",
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
