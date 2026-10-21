# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pyscada.thread import PROTOCOL_ID
from pyscada.thread.models import ThreadDevice, ExtendedThreadDevice
from pyscada.thread.models import ThreadVariable, ExtendedThreadVariable
from pyscada.admin import DeviceAdmin
from pyscada.admin import CoreVariableAdmin
from pyscada.admin import admin_site
from pyscada.models import Device, DeviceProtocol
from django.contrib import admin
import logging

logger = logging.getLogger(__name__)


class ThreadDeviceAdminInline(admin.StackedInline):
    model = ThreadDevice


class ThreadDeviceAdmin(DeviceAdmin):
    list_display = DeviceAdmin.list_display + (
        "ipv6_address",
        "port",
    )

    def ipv6_address(self, obj):
        return obj.threaddevice.ipv6_address

    def port(self, obj):
        return obj.threaddevice.port

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "protocol":
            kwargs["queryset"] = DeviceProtocol.objects.filter(pk=PROTOCOL_ID)
            db_field.default = PROTOCOL_ID
        return super(ThreadDeviceAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )

    def get_queryset(self, request):
        """Only list Thread devices."""
        qs = super(ThreadDeviceAdmin, self).get_queryset(request)
        return qs.filter(protocol_id=PROTOCOL_ID).select_related("threaddevice")

    inlines = [ThreadDeviceAdminInline]


class ThreadVariableAdminInline(admin.StackedInline):
    model = ThreadVariable


class ThreadVariableAdmin(CoreVariableAdmin):
    list_display = CoreVariableAdmin.list_display + ("resource",)

    def resource(self, obj):
        return obj.threadvariable.resource

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "device":
            kwargs["queryset"] = Device.objects.filter(protocol=PROTOCOL_ID)
        return super(ThreadVariableAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )

    def get_queryset(self, request):
        """Only list variables of Thread devices."""
        qs = super(ThreadVariableAdmin, self).get_queryset(request)
        return qs.filter(device__protocol_id=PROTOCOL_ID).select_related(
            "threadvariable"
        )

    inlines = [ThreadVariableAdminInline]


admin_site.register(ExtendedThreadDevice, ThreadDeviceAdmin)
admin_site.register(ExtendedThreadVariable, ThreadVariableAdmin)
