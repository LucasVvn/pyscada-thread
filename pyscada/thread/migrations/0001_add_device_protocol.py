# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from pyscada.thread import PROTOCOL_ID

from django.db import migrations


def forwards_func(apps, schema_editor):
    DeviceProtocol = apps.get_model("pyscada", "DeviceProtocol")
    db_alias = schema_editor.connection.alias
    if not DeviceProtocol.objects.using(db_alias).filter(pk=PROTOCOL_ID):
        DeviceProtocol.objects.using(db_alias).bulk_create(
            [
                DeviceProtocol(
                    pk=PROTOCOL_ID,
                    protocol="thread",
                    description="Thread (CoAP over UDP/IPv6)",
                    app_name="pyscada.thread",
                    device_class="pyscada.thread.device",
                    daq_daemon=True,
                    single_thread=True,
                ),
            ]
        )


def reverse_func(apps, schema_editor):
    DeviceProtocol = apps.get_model("pyscada", "DeviceProtocol")
    db_alias = schema_editor.connection.alias
    DeviceProtocol.objects.using(db_alias).filter(protocol="thread").delete()


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("pyscada", "0059_auto_20200211_1049"),
    ]

    operations = [
        migrations.RunPython(forwards_func, reverse_func),
    ]
