# -*- coding: utf-8 -*-
"""
Nœud Thread simulé : petit serveur CoAP pour tester le plugin sans matériel.

    python -m pyscada.thread.simulator --bind ::1 --port 5683

Ressources :
    GET /temperature   texte brut, ex. « 21.4 » (varie légèrement à chaque lecture)
    GET /mesures       JSON, ex. {"temperature": 21.4, "humidite": 48}
    GET/PUT /relais    « 0 » ou « 1 »
"""
from __future__ import unicode_literals

import argparse
import asyncio
import json
import random

import aiocoap
import aiocoap.resource as resource


class TemperatureResource(resource.Resource):
    def __init__(self, value=21.4, noise=0.2):
        super().__init__()
        self.value = value
        self.noise = noise

    async def render_get(self, request):
        self.value = round(self.value + random.uniform(-self.noise, self.noise), 2)
        return aiocoap.Message(
            code=aiocoap.CONTENT, payload=str(self.value).encode("utf-8")
        )


class MeasuresResource(resource.Resource):
    def __init__(self, temperature):
        super().__init__()
        self.temperature = temperature

    async def render_get(self, request):
        payload = {"temperature": self.temperature.value, "humidite": 48}
        return aiocoap.Message(
            code=aiocoap.CONTENT, payload=json.dumps(payload).encode("utf-8")
        )


class RelayResource(resource.Resource):
    def __init__(self):
        super().__init__()
        self.state = 0

    async def render_get(self, request):
        return aiocoap.Message(code=aiocoap.CONTENT, payload=str(self.state).encode())

    async def render_put(self, request):
        text = request.payload.decode("utf-8").strip()
        if text not in ("0", "1"):
            return aiocoap.Message(code=aiocoap.BAD_REQUEST, payload=b"0 or 1 expected")
        self.state = int(text)
        return aiocoap.Message(code=aiocoap.CHANGED)


def build_site(temperature=21.4, noise=0.2):
    site = resource.Site()
    temp = TemperatureResource(temperature, noise)
    site.add_resource(["temperature"], temp)
    site.add_resource(["mesures"], MeasuresResource(temp))
    site.add_resource(["relais"], RelayResource())
    return site


async def start_server(bind="::1", port=5683, site=None):
    """Démarre le nœud simulé et renvoie le contexte aiocoap (à fermer avec shutdown())."""
    if site is None:
        site = build_site()
    return await aiocoap.Context.create_server_context(site, bind=(bind, port))


async def _main(bind, port):
    await start_server(bind, port)
    print(f"Nœud Thread simulé sur coap://[{bind}]:{port}")
    await asyncio.get_running_loop().create_future()


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--bind", default="::1")
    parser.add_argument("--port", type=int, default=5683)
    args = parser.parse_args()
    try:
        asyncio.run(_main(args.bind, args.port))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
