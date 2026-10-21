# -*- coding: utf-8 -*-
"""
Client CoAP synchrone pour le démon PyScada.

Le démon appelle les handlers de façon synchrone. aiocoap est asynchrone :
on fait donc tourner une boucle asyncio dans un thread dédié et on lui
soumet les requêtes avec run_coroutine_threadsafe.
"""
from __future__ import unicode_literals

import asyncio
import threading
import logging

logger = logging.getLogger(__name__)

driver_ok = True
try:
    import aiocoap
except ImportError:
    logger.error("Cannot import aiocoap", exc_info=True)
    driver_ok = False


class CoapRunner:
    """
    Boucle asyncio dans un thread, partagée par toutes les requêtes du process.
    """

    def __init__(self):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._loop.run_forever, name="pyscada-thread-coap", daemon=True
        )
        self._thread.start()
        self._client = None

    def run(self, coro, timeout=None):
        """Exécute une coroutine dans la boucle CoAP et attend son résultat."""
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout)

    async def _client_context(self):
        if self._client is None:
            self._client = await aiocoap.Context.create_client_context()
        return self._client

    async def _request(self, code, uri, payload=b""):
        context = await self._client_context()
        message = aiocoap.Message(code=code, uri=uri, payload=payload)
        return await context.request(message).response

    def get(self, uri, timeout):
        """GET uri, renvoie la réponse aiocoap (code, payload)."""
        return self.run(
            asyncio.wait_for(self._request(aiocoap.GET, uri), timeout), timeout + 1
        )

    def stop(self):
        if self._client is not None:
            try:
                self.run(self._client.shutdown(), 5)
            except Exception:
                logger.debug("CoAP client shutdown failed", exc_info=True)
            self._client = None
        self._loop.call_soon_threadsafe(self._loop.stop)


_runner = None


def get_runner():
    """Un seul runner par process (chaque device Thread a son propre process)."""
    global _runner
    if _runner is None:
        _runner = CoapRunner()
    return _runner


def parse_payload(payload, payload_format=0, json_key=None):
    """
    Convertit le contenu d'une réponse CoAP en valeur PyScada.
    payload_format : 0 texte brut (« 21.4 », « 1 », « on »), 1 JSON.
    """
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    payload = payload.strip()
    if payload_format == 1:
        import json

        value = json.loads(payload)
        if json_key:
            for key in json_key.split():
                if isinstance(value, list):
                    value = value[int(key.strip("[]"))]
                else:
                    value = value[key]
        return _to_number(value)
    return _to_number(payload)


def _to_number(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip().lower()
    if text in ("true", "on"):
        return True
    if text in ("false", "off"):
        return False
    try:
        return int(text)
    except ValueError:
        return float(text)
