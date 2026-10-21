# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pyscada.models import Device
from . import PROTOCOL_ID

from django.db import models

import logging

logger = logging.getLogger(__name__)


class ThreadDevice(models.Model):
    """
    Paramètres d'un capteur ou actionneur Thread joint en CoAP.
    """

    thread_device = models.OneToOneField(
        Device, null=True, blank=True, on_delete=models.CASCADE
    )
    ipv6_address = models.GenericIPAddressField(
        protocol="IPv6",
        verbose_name="IPv6 address",
        help_text="Stable IPv6 address of the node (mesh prefix, not link-local), e.g. fd12::a1",
    )
    port = models.PositiveIntegerField(default=5683, help_text="CoAP port of the node")
    timeout = models.FloatField(
        default=5.0, help_text="Time to wait for a CoAP response, in seconds"
    )
    retries = models.PositiveSmallIntegerField(
        default=2, help_text="Number of new attempts after a failed request"
    )

    protocol_id = PROTOCOL_ID

    def parent_device(self):
        try:
            return self.thread_device
        except:
            return None

    def base_uri(self):
        return f"coap://[{self.ipv6_address}]:{self.port}"

    def __str__(self):
        return self.thread_device.short_name


class ExtendedThreadDevice(Device):
    class Meta:
        proxy = True
        verbose_name = "Thread Device"
        verbose_name_plural = "Thread Devices"
