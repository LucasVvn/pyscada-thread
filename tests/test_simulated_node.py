# -*- coding: utf-8 -*-
"""Lecture d'un nœud Thread simulé, de bout en bout (modèles → handler → CoAP)."""
from django.test import TestCase

from .helpers import SimulatedNode, device_instance, make_device, make_variable


class SimulatedNodeReadTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.node = SimulatedNode().start()

    @classmethod
    def tearDownClass(cls):
        cls.node.stop()
        super().tearDownClass()

    def test_read_plain_and_json(self):
        device = make_device(self.node.port)
        temperature = make_variable(device, "temperature", "/temperature")
        humidite = make_variable(
            device, "humidite", "mesures", payload_format=1, json_key="humidite"
        )
        dev = device_instance(device)

        updated = dev.request_data()

        values = {v.name: v.value for v in updated}
        self.assertEqual(values, {"temperature": 21.4, "humidite": 48})
        self.assertIn(temperature.pk, dev.variables)
        self.assertIn(humidite.pk, dev.variables)


class SimulatedNodeWriteTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.node = SimulatedNode().start()

    @classmethod
    def tearDownClass(cls):
        cls.node.stop()
        super().tearDownClass()

    def test_put_relay(self):
        device = make_device(self.node.port)
        relais = make_variable(
            device, "relais", "/relais", value_class="BOOLEAN", writeable=True
        )
        dev = device_instance(device)

        updated = dev.write_data(relais.pk, 1, task=None)

        self.assertEqual([v.pk for v in updated], [relais.pk])
        self.assertEqual(self.node.site._resources[("relais",)].state, 1)


class SimulatedNodeResponseCodeTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.node = SimulatedNode().start()

    @classmethod
    def tearDownClass(cls):
        cls.node.stop()
        super().tearDownClass()

    def test_unknown_resource_is_not_recorded(self):
        device = make_device(self.node.port)
        make_variable(device, "inconnue", "/n-existe-pas")
        dev = device_instance(device)

        with self.assertLogs("pyscada.thread.devices", "WARNING") as logs:
            updated = dev.request_data()

        self.assertEqual(updated, [])
        self.assertIn("4.04 Not Found", logs.output[0])

    def test_refused_put_is_failed(self):
        device = make_device(self.node.port)
        relais = make_variable(device, "relais", "/relais", writeable=True)
        dev = device_instance(device)

        with self.assertLogs("pyscada.thread.devices", "WARNING") as logs:
            updated = dev.write_data(relais.pk, 7, task=None)

        self.assertEqual(updated, [])
        self.assertIn("4.00 Bad Request", logs.output[0])
