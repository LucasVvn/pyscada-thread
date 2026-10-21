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
