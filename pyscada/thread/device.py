# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from pyscada.device import GenericDevice
from .coap import driver_ok
from .devices import GenericDevice as GenericHandlerDevice

import logging

logger = logging.getLogger(__name__)


class Device(GenericDevice):
    """
    Thread device
    """

    def __init__(self, device):
        self.driver_ok = driver_ok
        self.handler_class = GenericHandlerDevice
        super().__init__(device)
