"""Servicio del agente: sustituye a Agent Runtime dentro del host Linux.

Expone, solo en la red interna de Docker, las tres operaciones que el puente
usaba de Agent Runtime:

  POST /sesiones                      crear sesion        -> {"id": ...}
  POST /consulta                      un turno, en NDJSON (un evento por linea)
  GET  /sesiones/{user_id}/{sid}      la sesion con su estado (puntos 2 y 3)
  GET  /health                        diagnostico

Las sesiones y la memoria viven en la base de datos de DB_URL. Los puntos 2
y 3 de Check Point AI Guardrails corren aqui, dentro de los agentes.
"""

import json
import logging

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import create_async_engine

from bank_agents.agent import root_agent
from bank_agents.memoria import construir_memoria
from bank_agents.shared import config
from bank_agents.shared.guardrails import activo

logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
log = logging.getLogger("servidor")

engine = create_async_engine(config.DB_URL, pool_pre_ping=True)
sesiones = DatabaseSessionService(db_engine=engine)
memoria = construir_memoria(engine)
runner = Runner(agent=root_agent, app_name=config.APP_NAME,
                session_service=sesiones, memory_service=memoria)

app = FastAPI(title="Banca Digital - agente", version="1.0.0")


class NuevaSesion(BaseModel):
    user_id: str


class Consulta(BaseModel):
    user_id: str
    session_id: str
    message: str


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "proveedor": config.LLM_PROVIDER,
            "perfil": config.PERFIL_AGENTE, "guardrails": activo()}


@app.post("/sesiones")
async def crear_sesion(p: NuevaSesion) -> dict:
    s = await sesiones.create_session(app_name=config.APP_NAME, user_id=p.user_id)
    return {"id": s.id, "user_id": s.user_id}


@app.get("/sesiones/{user_id}/{session_id}")
async def leer_sesion(user_id: str, session_id: str) -> dict:
    s = await sesiones.get_session(app_name=config.APP_NAME, user_id=user_id,
                                   session_id=session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="sesion no encontrada")
    return {"id": s.id, "user_id": s.user_id, "state": dict(s.state)}


@app.post("/consulta")
async def consulta(c: Consulta) -> StreamingResponse:
    s = await sesiones.get_session(app_name=config.APP_NAME, user_id=c.user_id,
                                   session_id=c.session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="sesion no encontrada")
    mensaje = types.Content(role="user", parts=[types.Part(text=c.message)])

    async def eventos():
        try:
            async for ev in runner.run_async(user_id=c.user_id,
                                             session_id=c.session_id,
                                             new_message=mensaje):
                yield json.dumps(ev.model_dump(mode="json", exclude_none=True),
                                 ensure_ascii=False) + "\n"
        except Exception as e:  # noqa: BLE001
            # Un fallo del modelo (cuota, red, clave) llega como evento de
            # error, igual que los error_code que ADK pone dentro del stream.
            log.exception("turno fallido")
            yield json.dumps({"author": "servidor",
                              "error_code": type(e).__name__,
                              "error_message": str(e)[:500]}) + "\n"

    return StreamingResponse(eventos(), media_type="application/x-ndjson")
