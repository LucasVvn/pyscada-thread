# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pyscada.models import Device, Variable
from pyscada.thread.models import (
    ThreadDevice,
    ThreadVariable,
    ExtendedThreadVariable,
    ExtendedThreadDevice,
)

from django.dispatch import receiver
from django.db.models.signals import post_save
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ThreadDevice)
@receiver(post_save, sender=ThreadVariable)
@receiver(post_save, sender=ExtendedThreadVariable)
@receiver(post_save, sender=ExtendedThreadDevice)
def _reinit_daq_daemons(sender, instance, **kwargs):
    """
    update the daq daemon configuration when changes be applied in the models
    """
    if type(instance) is ThreadDevice:
        post_save.send_robust(sender=Device, instance=instance.thread_device)
    elif type(instance) is ThreadVariable:
        post_save.send_robust(sender=Variable, instance=instance.thread_variable)
    elif type(instance) is ExtendedThreadVariable:
        post_save.send_robust(
            sender=Variable, instance=Variable.objects.get(pk=instance.pk)
        )
    elif type(instance) is ExtendedThreadDevice:
        post_save.send_robust(
            sender=Device, instance=Device.objects.get(pk=instance.pk)
        )
