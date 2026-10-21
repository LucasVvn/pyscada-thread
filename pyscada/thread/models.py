# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pyscada.models import Device, Variable
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


class ThreadVariable(models.Model):
    """
    Ressource CoAP lue ou écrite pour une variable PyScada.
    """

    thread_variable = models.OneToOneField(
        Variable, null=True, blank=True, on_delete=models.CASCADE
    )
    resource = models.CharField(
        max_length=254,
        help_text="CoAP resource path on the node, e.g. /temperature",
    )
    payload_format_choices = (
        (0, "Plain text"),
        (1, "JSON"),
    )
    payload_format = models.PositiveSmallIntegerField(
        default=0, choices=payload_format_choices
    )
    json_key = models.CharField(
        max_length=254,
        null=True,
        blank=True,
        help_text="With JSON payloads: key of the value, nested keys separated by spaces",
    )

    protocol_id = PROTOCOL_ID

    def path(self):
        return "/" + self.resource.strip("/")

    def __str__(self):
        return self.id.__str__() + "-" + self.thread_variable.name


class ExtendedThreadVariable(Variable):
    class Meta:
        proxy = True
        verbose_name = "Thread Variable"
        verbose_name_plural = "Thread Variables"

    def resource(self):
        return self.threadvariable.resource
