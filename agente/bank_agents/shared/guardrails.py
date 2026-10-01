"""Cliente de Check Point AI Guardrails.

    POST https://api.lakera.ai/v2/guard
    {"messages": [...], "project_id": "...", "breakdown": true}
 -> {"flagged": bool, "action": "enforce"|"detect", "breakdown": [...]}

En Detect Mode 'flagged' llega False aunque los detectores disparen: lo que
se vio sale del breakdown; el corte sale de flagged + action.
"""

import logging
import os

import httpx

URL = os.environ.get("LAKERA_URL", "https://api.lakera.ai/v2/guard")
KEY = os.environ.get("LAKERA_GUARD_API_KEY", "")
PROJECT = os.environ.get("LAKERA_PROJECT_ID", "")
MODO = os.environ.get("LAKERA_MODO", "auto")          # auto | observar | bloquear
TIMEOUT = float(os.environ.get("LAKERA_TIMEOUT", "4"))
FAIL_OPEN = os.environ.get("LAKERA_FAIL_OPEN", "1") == "1"

log = logging.getLogger("guardrails")
_cliente = httpx.AsyncClient(timeout=TIMEOUT) if KEY else None


def activo() -> bool:
    return bool(KEY and _cliente)


async def evaluar(messages: list[dict], punto: str = "?") -> dict | None:
    """Veredicto completo de la politica, corte o no. None si no hay veredicto."""
    if not activo():
        return None
    cuerpo = {"messages": messages, "breakdown": True}
    if PROJECT:
        cuerpo["project_id"] = PROJECT
    try:
        r = await _cliente.post(URL, json=cuerpo,
                                headers={"Authorization": f"Bearer {KEY}"})
        r.raise_for_status()
        datos = r.json()
    except Exception as e:  # noqa: BLE001
        log.warning("guardrails punto=%s sin veredicto: %s", punto, e)
        if FAIL_OPEN:
            return None
        return {"punto": punto, "detectores": ["sin_veredicto"],
                "confianza": [], "accion": None, "bloqueado": True}

    disparados = [d for d in datos.get("breakdown", []) if d.get("detected")]
    detectores = sorted({d.get("detector_type", "?") for d in disparados})
    confianza = sorted({d.get("result", "?") for d in disparados})
    accion = datos.get("action")
    marcado = bool(datos.get("flagged"))

    if MODO == "observar":
        bloqueado = False
    elif MODO == "bloquear":
        bloqueado = bool(detectores)
    else:
        bloqueado = marcado and accion == "enforce"

    if detectores:
        log.warning("guardrails punto=%s action=%s flagged=%s detectores=%s %s",
                    punto, accion, marcado, detectores, confianza)

    return {"punto": punto, "detectores": detectores, "confianza": confianza,
            "accion": accion, "bloqueado": bloqueado}


async def revisar(messages: list[dict], punto: str = "?") -> dict | None:
    """El veredicto solo si hay que BLOQUEAR. None = dejar pasar."""
    v = await evaluar(messages, punto)
    return v if v and v["bloqueado"] else None


def anotar(estado, veredicto, invocacion) -> None:
    """Deja la deteccion en el estado de la sesion para que el puente la lea."""
    if not veredicto or not veredicto.get("detectores"):
        return
    lista = list(estado.get("guardrails") or [])
    lista.append({**veredicto, "inv": invocacion})
    estado["guardrails"] = lista[-40:]


def como_mensajes(texto: str, rol: str = "user") -> list[dict]:
    return [{"role": rol, "content": texto}]
