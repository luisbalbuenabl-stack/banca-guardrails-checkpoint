"""Imitacion local de POST /v2/guard, solo para las pruebas de humo.

Marca como prompt_attack cualquier mensaje que contenga la palabra ATAQUE o
el texto inyectado de los documentos hipotecario (SYSTEM OVERRIDE) y de
portabilidad (NOTA OPERATIVA PARA EL ASISTENTE). Responde con
la misma forma que Check Point AI Guardrails: flagged, action y breakdown.
GUARD_ACCION=detect (por defecto) o enforce imita el Project mode.

Uso: uvicorn guard_simulado:app --port 9000   (y LAKERA_URL=http://.../v2/guard)
"""

import json
import os

from fastapi import FastAPI, Request

app = FastAPI()
ACCION = os.environ.get("GUARD_ACCION", "detect")
MARCAS = ("ATAQUE", "SYSTEM OVERRIDE", "NOTA OPERATIVA PARA EL ASISTENTE")
VISTOS: list[dict] = []


@app.post("/v2/guard")
async def guard(req: Request) -> dict:
    cuerpo = await req.json()
    texto = json.dumps(cuerpo.get("messages", []), ensure_ascii=False)
    detectado = any(m in texto for m in MARCAS)
    roles = [m.get("role") for m in cuerpo.get("messages", [])]
    VISTOS.append({"roles": roles, "detectado": detectado})
    return {
        "flagged": detectado and ACCION == "enforce",
        "action": ACCION,
        "breakdown": [{"detector_type": "prompt_attack", "detected": detectado,
                       "result": "l1_confident" if detectado else "l5_unlikely"}],
    }


@app.get("/vistos")
def vistos() -> list[dict]:
    return VISTOS
