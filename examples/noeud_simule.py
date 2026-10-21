# -*- coding: utf-8 -*-
"""
Crée un device Thread d'exemple qui interroge le nœud simulé
(python -m pyscada.thread.simulator) sur coap://[::1]:5683.

    cd /var/www/pyscada/PyScadaServer
    sudo -u pyscada /home/pyscada/.venv/bin/python manage.py shell < ~/Documents/pyscada-thread/examples/noeud_simule.py

Relancer ensuite le démon pour qu'il prenne le device en compte.
"""
from pyscada.models import Device, DeviceProtocol, Unit, Variable
from pyscada.thread import PROTOCOL_ID
from pyscada.thread.models import ThreadDevice, ThreadVariable

protocol = DeviceProtocol.objects.get(pk=PROTOCOL_ID)
device, _ = Device.objects.get_or_create(
    short_name="noeud-simule",
    defaults=dict(
        protocol=protocol,
        description="Nœud Thread simulé (pyscada.thread.simulator)",
        polling_interval=60,
        active=True,
    ),
)
ThreadDevice.objects.update_or_create(
    thread_device=device,
    defaults=dict(ipv6_address="::1", port=5683, timeout=5, retries=2, mode=0),
)

celsius, _ = Unit.objects.get_or_create(unit="°C", defaults={"description": "Celsius"})
sans_unite, _ = Unit.objects.get_or_create(unit="-", defaults={"description": "Sans unité"})

for name, resource, unit, value_class, writeable, cov in [
    ("SimuTemperature", "/temperature", celsius, "FLOAT32", False, 0.1),
    ("SimuRelais", "/relais", sans_unite, "BOOLEAN", True, 0),
]:
    variable, _ = Variable.objects.get_or_create(
        name=name,
        defaults=dict(
            device=device,
            unit=unit,
            value_class=value_class,
            writeable=writeable,
            cov_increment=cov,
            active=True,
        ),
    )
    ThreadVariable.objects.update_or_create(
        thread_variable=variable, defaults=dict(resource=resource, payload_format=0)
    )

print(f"Device {device.short_name} prêt, variables : SimuTemperature, SimuRelais")
