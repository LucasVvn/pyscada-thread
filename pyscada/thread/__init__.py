# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__version__ = "0.1.0"
__author__ = "Lucas Vivien"
__email__ = "lvivien001@iutbayonne.univ-pau.fr"
__description__ = "Thread (CoAP) extension for PyScada a Python and Django based Open Source SCADA System"
__app_name__ = "Thread"

# Identifiant du protocole dans pyscada.DeviceProtocol.
# Valeurs déjà prises par le cœur et les plugins officiels :
# 1-6, 8, 10-12, 14-16, 18-20, 94, 96, 97.
PROTOCOL_ID = 30

parent_process_list = [
    {
        "pk": PROTOCOL_ID,
        "label": "pyscada." + __app_name__.lower(),
        "process_class": "pyscada." + __app_name__.lower() + ".worker.Process",
        "process_class_kwargs": '{"dt_set":30}',
        "enabled": True,
    }
]
