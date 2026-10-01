"""Cliente del servicio del agente (agente/servidor.py).

Ofrece los mismos tres metodos que el objeto de Agent Runtime que usaba el
puente, para que su codigo no cambie:

  await agente.async_create_session(user_id=...)            -> {"id": ...}
  async for ev in agente.async_stream_query(user_id=..., session_id=..., message=...)
  await agente.async_get_session(user_id=..., session_id=...) -> {"state": ...}
"""

import json
import os

import httpx

AGENTE_URL = os.environ.get("AGENTE_URL", "http://agente:8000")
# Un turno multi-agente puede tardar; el puente tiene su propio limite.
TIMEOUT = httpx.Timeout(float(os.environ.get("AGENTE_TIMEOUT", "300")), connect=10)


class AgenteRemoto:
    def __init__(self, url: str = AGENTE_URL) -> None:
        self.url = url.rstrip("/")
        self._http = httpx.AsyncClient(base_url=self.url, timeout=TIMEOUT)

    async def async_create_session(self, user_id: str) -> dict:
        r = await self._http.post("/sesiones", json={"user_id": user_id})
        r.raise_for_status()
        return r.json()

    async def async_get_session(self, user_id: str, session_id: str) -> dict:
        r = await self._http.get(f"/sesiones/{user_id}/{session_id}")
        r.raise_for_status()
        return r.json()

    async def async_stream_query(self, user_id: str, session_id: str, message: str):
        cuerpo = {"user_id": user_id, "session_id": session_id, "message": message}
        async with self._http.stream("POST", "/consulta", json=cuerpo) as r:
            r.raise_for_status()
            async for linea in r.aiter_lines():
                if linea.strip():
                    yield json.loads(linea)

    async def health(self) -> dict:
        r = await self._http.get("/health")
        r.raise_for_status()
        return r.json()
