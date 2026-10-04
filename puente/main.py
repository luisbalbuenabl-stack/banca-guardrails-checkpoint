"""Puente del agente bancario.

  /consola        la consola web para hablar con el agente en vivo
  /consola/chat   el endpoint de esa consola (Bearer)
  /health         diagnostico

Aqui viven los puntos 1 (lo que entra) y 4 (la interaccion que sale).
Los puntos 2 y 3 corren dentro del servicio del agente y dejan su veredicto
en el estado de la sesion; el puente los lee de ahi para mostrarlos.
"""

import asyncio
import os
import random
from pathlib import Path

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from agente_cliente import AgenteRemoto
from guardrails import activo, como_mensajes, evaluar

PUENTE_TOKEN = os.environ["PUENTE_TOKEN"]

# La identidad la fija el servidor, nunca el cliente: es lo que aisla la
# memoria de cada usuario.
USER_CONSOLA = "cliente-consola"

RECHAZO = ("No puedo ayudarte con esa solicitud. Si necesitas informacion "
           "sobre tu cuenta, tus tarjetas o nuestros productos, con gusto "
           "te apoyo.")
RETENIDA = ("Por seguridad no puedo mostrar esa informacion en este canal. "
            "Un asesor puede ayudarte a verificarla.")

agente = AgenteRemoto()

CONSOLA = Path(__file__).with_name("consola.html")

app = FastAPI(title="Banca Digital - puente", version="2.2.0")

# Si el servicio del agente responde 429 o 503 (saturado), no es una
# respuesta del agente: se espera y se reintenta, para que la consola mida al
# agente y no la capacidad del servidor.
REINTENTOS = 6


async def con_reintento(llamada):
    espera = 2.0
    for intento in range(REINTENTOS):
        try:
            return await llamada()
        except httpx.HTTPStatusError as e:
            if e.response.status_code not in (429, 503) or intento == REINTENTOS - 1:
                raise
            await asyncio.sleep(espera + random.random())
            espera = min(espera * 2, 30.0)


class Turno(BaseModel):
    message: str
    sessionId: str | None = None


def _autorizar(authorization: str) -> None:
    if authorization != f"Bearer {PUENTE_TOKEN}":
        raise HTTPException(status_code=403, detail="token invalido o ausente")


def _resumen(v: dict | None) -> dict | None:
    if not v or not v.get("detectores"):
        return None
    return {"punto": str(v["punto"]), "detectores": list(v["detectores"]),
            "bloqueado": bool(v.get("bloqueado"))}


def agrupar(entradas: list[dict]) -> list[dict]:
    """Una entrada por punto: detectores unidos, bloqueado si alguno corto."""
    por_punto: dict[str, dict] = {}
    for e in entradas:
        p = por_punto.setdefault(e["punto"], {"punto": e["punto"],
                                              "detectores": [], "bloqueado": False})
        for d in e["detectores"]:
            if d not in p["detectores"]:
                p["detectores"].append(d)
        p["bloqueado"] = p["bloqueado"] or e["bloqueado"]
    return [por_punto[k] for k in sorted(por_punto)]


async def atender(turno: Turno, user_id: str, detalle: bool = True) -> dict:
    sid = turno.sessionId
    if not sid:
        sesion = await con_reintento(
            lambda: agente.async_create_session(user_id=user_id))
        sid = sesion["id"]

    vistos: list[dict] = []
    modo = ""

    # PUNTO 1 - lo que entra, antes de gastar tokens del modelo.
    v1 = await evaluar(como_mensajes(turno.message), punto="1",
                      meta={"session_id": sid, "user_id": user_id, "superficie": "entrada"})
    if v1 and v1.get("accion"):
        modo = v1["accion"]
    if (r := _resumen(v1)):
        vistos.append(r)
    if v1 and v1.get("bloqueado"):
        return {"sessionId": sid, "message": RECHAZO, "modo": modo,
                "guardrails": agrupar(vistos), "flujo": []}

    async def turno_agente():
        partes, invocaciones, flujo = [], set(), []
        async for evento in agente.async_stream_query(
                user_id=user_id, session_id=sid, message=turno.message):
            if evento.get("invocation_id"):
                invocaciones.add(evento["invocation_id"])
            autor = evento.get("author", "")
            if autor == "user":
                continue
            # El recorrido del turno, para la consola: delegaciones, herramientas
            # y errores del modelo que llegan dentro del stream.
            if evento.get("error_code"):
                flujo.append({"tipo": "error", "agente": autor,
                              "valor": str(evento["error_code"])})
            for parte in (evento.get("content") or {}).get("parts", []):
                if parte.get("text"):
                    partes.append(parte["text"])
                llamada = parte.get("function_call")
                if llamada:
                    nombre = llamada.get("name", "")
                    if nombre == "transfer_to_agent":
                        flujo.append({"tipo": "handoff", "agente": autor,
                                      "valor": (llamada.get("args") or {}).get("agent_name", "")})
                    else:
                        flujo.append({"tipo": "tool", "agente": autor, "valor": nombre})
                resp = parte.get("function_response")
                if resp and resp.get("name") != "transfer_to_agent":
                    flujo.append({"tipo": "tool_resp", "agente": autor,
                                  "valor": resp.get("name", "")})
        return partes, invocaciones, flujo

    partes, invocaciones, flujo = await con_reintento(turno_agente)
    texto = "".join(partes).strip() or "(sin respuesta del agente)"

    # PUNTOS 2 y 3 - los dejo el agente en el estado de la sesion,
    # marcados con el invocation_id de este turno, para mostrarlos en la
    # consola.
    if detalle:
        sesion = await con_reintento(
            lambda: agente.async_get_session(user_id=user_id, session_id=sid))
        for e in (sesion.get("state") or {}).get("guardrails", []):
            if e.get("inv") in invocaciones and (r := _resumen(e)):
                vistos.append(r)

    # PUNTO 4 - la interaccion completa, cada mensaje con su rol.
    v4 = await evaluar([{"role": "user", "content": turno.message},
                        {"role": "assistant", "content": texto}], punto="4",
                        meta={"session_id": sid, "user_id": user_id, "superficie": "salida"})
    if (r := _resumen(v4)):
        vistos.append(r)
    if v4 and v4.get("bloqueado"):
        texto = RETENIDA

    return {"sessionId": sid, "message": texto, "modo": modo,
            "guardrails": agrupar(vistos), "flujo": flujo}


@app.get("/health")
async def health() -> dict:
    try:
        estado_agente = (await agente.health()).get("status", "?")
    except Exception as e:  # noqa: BLE001
        estado_agente = f"sin respuesta: {type(e).__name__}"
    return {"status": "ok", "agente": estado_agente, "guardrails": activo()}


@app.get("/consola")
def consola() -> FileResponse:
    # Sin cache: cada recarga trae la version desplegada de la consola.
    return FileResponse(CONSOLA, media_type="text/html",
                        headers={"Cache-Control": "no-store"})


@app.post("/consola/chat")
async def consola_chat(turno: Turno,
                       authorization: str = Header(default="")) -> dict:
    _autorizar(authorization)
    return await atender(turno, USER_CONSOLA)
