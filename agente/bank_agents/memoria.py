"""Memoria del orquestador entre sesiones, en la base de datos local.

Sustituye a Vertex AI Memory Bank: guardar_turno() (punto 3) y recordar()
(punto 2) no cambian; solo cambia el servicio que hay detras.
"""

import logging

from google.adk.tools.tool_context import ToolContext

from bank_agents.memoria_sql import MemoriaSQL
from bank_agents.shared.guardrails import anotar, como_mensajes, contexto, evaluar

log = logging.getLogger("memoria")


def construir_memoria(engine) -> MemoriaSQL:
    """Servicio de memoria sobre el mismo motor de base de datos de las sesiones.

    servidor.py lo pasa al Runner como memory_service.
    """
    return MemoriaSQL(engine)


# Tamano maximo del turno que se inspecciona y se guarda.
TOPE = 8000


def _texto(eventos) -> str:
    """El texto de esos eventos: exactamente lo que se va a guardar."""
    trozos = []
    for e in eventos:
        for parte in (e.content.parts or []):
            if getattr(parte, "text", None):
                trozos.append(parte.text)
    return " ".join(trozos)


def _del_turno(callback_context) -> list:
    """Los eventos con texto de la invocacion en curso."""
    sesion = callback_context.session
    return [e for e in sesion.events
            if e.invocation_id == callback_context.invocation_id
            and e.content and e.content.parts]


async def guardar_turno(callback_context):
    """after_agent_callback: guarda el turno en la memoria del cliente.

    Solo se guardan los eventos de este turno, y solo si pasaron el punto 3:
    un turno retenido nunca llega a la memoria, ni ahora ni en el turno
    siguiente. Devuelve None para no alterar la respuesta del agente.
    """
    # PUNTO 3. Google documenta como mitigacion del envenenamiento de
    # memoria inspeccionar lo que se envia a la memoria. Se inspecciona
    # exactamente el texto que se guarda.
    del_turno = _del_turno(callback_context)
    texto = _texto(del_turno)
    if len(texto) > TOPE:
        # Lo que no se puede inspeccionar completo no se guarda.
        log.warning("memoria: turno de %d caracteres, no se guarda", len(texto))
        return None
    v = await evaluar(como_mensajes(texto), punto="3",
                      meta=contexto(callback_context)) if texto else None
    anotar(callback_context.state, v, callback_context.invocation_id)
    if v and v["bloqueado"]:
        # La sesion sigue; lo que no pasa el filtro no se consolida y
        # por tanto no contamina conversaciones futuras.
        log.warning("memoria: turno retenido en el punto 3")
        return None

    try:
        await callback_context.add_events_to_memory(events=del_turno)
    except Exception as exc:
        log.warning("memoria: no se pudo guardar el turno (%s)", exc)
    return None


async def recordar(consulta: str, tool_context: ToolContext) -> dict:
    """Consulta lo que el banco recuerda de este cliente de conversaciones previas.

    Usala cuando el cliente se refiera a algo anterior ("lo de siempre", "mi
    cuenta de nomina", "como la vez pasada") o cuando necesites una preferencia
    suya que no aparece en este turno.

    Args:
        consulta: que buscar, en lenguaje natural. Por ejemplo
            "cuenta preferida del cliente" o "reclamacion anterior".

    Returns:
        dict con 'status' y, si hay coincidencias, 'recuerdos' con los
        fragmentos encontrados.
    """
    try:
        respuesta = await tool_context.search_memory(consulta)
    except Exception as exc:
        log.warning("memoria: fallo la consulta (%s)", exc)
        return {"status": "error", "detalle": str(exc)}

    recuerdos = []
    for entrada in (getattr(respuesta, "memories", None) or []):
        partes = getattr(getattr(entrada, "content", None), "parts", None) or []
        texto = " ".join(p.text for p in partes if getattr(p, "text", None))
        if texto.strip():
            recuerdos.append(texto.strip())

    if not recuerdos:
        return {"status": "sin_datos"}
    return {"status": "ok", "recuerdos": recuerdos}
