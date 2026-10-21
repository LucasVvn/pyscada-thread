# -*- coding: utf-8 -*-
"""
Crée un device Thread d'exemple qui interroge le nœud simulé
(python -m pyscada.thread.simulator) sur coap://[::1]:5683, ses variables,
et une page « thread » de l'IHM avec un graphique température + CO2.

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
        polling_interval=10,
        active=True,
    ),
)
ThreadDevice.objects.update_or_create(
    thread_device=device,
    defaults=dict(ipv6_address="::1", port=5683, timeout=5, retries=2, mode=0),
)

celsius, _ = Unit.objects.get_or_create(unit="°C", defaults={"description": "Celsius"})
ppm, _ = Unit.objects.get_or_create(unit="ppm", defaults={"description": "Parties par million"})
sans_unite, _ = Unit.objects.get_or_create(unit="-", defaults={"description": "Sans unité"})

for name, resource, unit, value_class, writeable, cov in [
    ("SimuTemperature", "/temperature", celsius, "FLOAT32", False, 0),
    ("SimuCO2", "/co2", ppm, "FLOAT32", False, 0),
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

# IHM : un graphique température (axe gauche) + CO2 (axe droit) sur une page « thread »
from pyscada.hmi.models import Chart, ChartAxis, Page, View, Widget, WidgetContent

chart, created = Chart.objects.get_or_create(title="Nœud Thread simulé")
if created:
    axe_temp = ChartAxis.objects.create(chart=chart, label="°C", position=0, show_plot_lines=1)
    axe_temp.variables.add(Variable.objects.get(name="SimuTemperature"))
    axe_co2 = ChartAxis.objects.create(chart=chart, label="ppm", position=1, show_plot_lines=1)
    axe_co2.variables.add(Variable.objects.get(name="SimuCO2"))
content = WidgetContent.objects.get(
    content_model=chart.__module__ + "." + chart.__class__.__name__, content_pk=chart.pk
)
page, _ = Page.objects.get_or_create(link_title="thread", defaults={"title": "Thread (simulation)", "position": 10})
Widget.objects.get_or_create(page=page, content=content, defaults={"title": "Température et CO2", "size": 4})
view, _ = View.objects.get_or_create(link_title="thread", defaults={"title": "Thread", "description": "Nœud Thread simulé"})
view.pages.add(page)

print(f"Device {device.short_name} prêt, variables : SimuTemperature, SimuCO2, SimuRelais")
print("IHM : vue « Thread », page « thread »")
