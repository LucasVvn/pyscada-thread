# -*- coding: utf-8 -*-
"""Nœud injoignable : délai, tentatives et message unique."""
import socket
from time import monotonic

from django.test import TestCase

from .helpers import SimulatedNode, device_instance, make_device, make_variable


class UnreachableNodeTest(TestCase):
    def setUp(self):
        # socket UDP qui reçoit mais ne répond jamais : simule un capteur muet
        self.silent = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        self.silent.bind(("::1", 0))
        self.port = self.silent.getsockname()[1]

    def tearDown(self):
        self.silent.close()

    def test_timeout_retries_and_skip(self):
        device = make_device(self.port, timeout=0.3, retries=1)
        make_variable(device, "temperature", "/temperature")
        make_variable(device, "humidite", "/humidite")
        dev = device_instance(device)

        start = monotonic()
        with self.assertLogs("pyscada.device", "INFO") as logs:
            updated = dev.request_data()
        elapsed = monotonic() - start

        self.assertEqual(updated, [])
        # 2 tentatives de 0,3 s pour la 1re variable, la 2e est sautée
        self.assertLess(elapsed, 1.2)
        self.assertGreaterEqual(elapsed, 0.6)
        self.assertEqual(len(logs.output), 1)
        self.assertIn("not accessible", logs.output[0])
        self.assertIn("after 2 attempt(s)", logs.output[0])

    def test_message_only_once_then_recovery(self):
        node = SimulatedNode().start()
        try:
            device = make_device(self.port, timeout=0.2, retries=0)
            make_variable(device, "temperature", "/temperature")
            dev = device_instance(device)

            with self.assertLogs("pyscada.device", "INFO") as logs:
                dev.request_data()
                dev.request_data()
                # le nœud revient (nouvelle adresse de port pour le test)
                dev.device.threaddevice.port = node.port
                self.assertEqual(len(dev.request_data()), 1)
                dev.request_data()

            self.assertEqual(len(logs.output), 2)
            self.assertIn("not accessible", logs.output[0])
            self.assertIn("Connected", logs.output[1])
        finally:
            node.stop()
