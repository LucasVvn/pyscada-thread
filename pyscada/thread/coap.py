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


class CoapResponseError(Exception):
    """Le nœud a répondu avec un code d'erreur CoAP (4.xx ou 5.xx)."""

    def __init__(self, uri, response):
        self.uri = uri
        self.code = response.code
        self.payload = response.payload
        detail = response.payload.decode("utf-8", "replace").strip()
        message = f"{uri} -> {response.code}"
        if detail:
            message += f" ({detail})"
        super().__init__(message)


def check_response(uri, response, expected):
    """
    Vérifie le code de réponse : 2.05 Content attendu pour un GET,
    2.04 Changed pour un PUT. Un autre code 2.xx est accepté, un 4.xx ou
    5.xx lève CoapResponseError.
    """
    if not response.code.is_successful():
        raise CoapResponseError(uri, response)
    if response.code != expected:
        logger.debug(f"{uri} -> {response.code}, {expected} expected")
    return response


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

    def request(self, code, uri, payload=b"", timeout=5.0):
        """Envoie une requête CoAP et renvoie la réponse aiocoap (code, payload)."""
        return self.run(
            asyncio.wait_for(self._request(code, uri, payload), timeout), timeout + 1
        )

    def get(self, uri, timeout):
        """GET, 2.05 Content attendu."""
        response = self.request(aiocoap.GET, uri, timeout=timeout)
        return check_response(uri, response, aiocoap.CONTENT)

    def put(self, uri, payload, timeout):
        """PUT, 2.04 Changed attendu."""
        response = self.request(aiocoap.PUT, uri, payload, timeout)
        return check_response(uri, response, aiocoap.CHANGED)

    def start_server(self, site, bind):
        """Démarre un serveur CoAP (mode push) et renvoie son contexte."""
        return self.run(aiocoap.Context.create_server_context(site, bind=bind), 10)

    def stop_server(self, context):
        try:
            self.run(context.shutdown(), 5)
        except Exception:
            logger.debug("CoAP server shutdown failed", exc_info=True)

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


def format_payload(value, payload_format=0, json_key=None):
    """
    Prépare le contenu d'un PUT : « 1 »/« 0 » pour un booléen, « 21 » plutôt que
    « 21.0 », ou un objet JSON {clé: valeur} si la variable est en JSON.
    """
    if isinstance(value, bool):
        value = int(value)
    elif isinstance(value, float) and value.is_integer():
        value = int(value)
    if payload_format == 1:
        import json

        if json_key:
            for key in reversed(json_key.split()):
                value = {key: value}
        return json.dumps(value).encode("utf-8")
    return str(value).encode("utf-8")


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
