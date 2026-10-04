"""Punto 2: entradas y salidas de herramientas.

Los nombres de los parametros son obligatorios: ADK pasa los argumentos de
los callbacks por palabra clave, asi que deben coincidir exactamente con los
documentados (tool, args, tool_context, tool_response).

Semantica del retorno, tambien documentada: un valor "truthy" CORTA la
cadena. En before_tool_callback ese dict sustituye al resultado de la
herramienta, que no llega a ejecutarse. En after_tool_callback sustituye a
la respuesta que veria el modelo.

FORMA DEL MENSAJE: la politica evalua por superficie, y la superficie se
deduce de la ESTRUCTURA del mensaje, no de una etiqueta. Una llamada a
herramienta solo llega a la superficie Tool Call -- donde vive Agent
Behavior Defense -- si viaja como 'tool_calls'. Con texto plano cae en
Assistant y el control agentico no se aplica nunca.
"""

import json

from bank_agents.shared.guardrails import anotar, contexto, evaluar

BLOQUEO_ENTRADA = {"status": "blocked",
                   "message": ("Operacion detenida por politica de seguridad. "
                               "No se ejecuto ninguna accion sobre la cuenta.")}
BLOQUEO_SALIDA = {"status": "blocked",
                  "message": ("El contenido recuperado fue retenido por "
                              "politica de seguridad.")}

TOPE = 4000


def _llamada(nombre, args, cid="c1"):
    """La llamada en el formato que identifica la superficie Tool Call."""
    return {"role": "assistant", "content": None,
            "tool_calls": [{"id": cid, "type": "function",
                            "function": {"name": nombre,
                                         "arguments": json.dumps(
                                             args or {}, ensure_ascii=False,
                                             default=str)[:TOPE]}}]}


def _legible(respuesta) -> str:
    """El resultado como texto legible: es lo que se ve en el evento del portal.

    Los documentos recuperados van primero y completos, uno por parrafo, para
    que en el registro se lea el documento envenenado tal como lo recibio el
    agente.
    """
    if isinstance(respuesta, dict) and isinstance(respuesta.get("fragmentos"), list):
        return "\n\n".join(str(f) for f in respuesta["fragmentos"])
    try:
        return json.dumps(respuesta, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(respuesta)


async def revisar_llamada(tool, args, tool_context):
    """before_tool_callback. Que herramienta se va a invocar, y con que.

    Aqui actua Tool Access Control: una herramienta fuera de la lista
    permitida se marca aunque sus argumentos sean inocentes.
    """
    v = await evaluar([_llamada(tool.name, args)], punto="2",
                      meta={**contexto(tool_context), "herramienta": tool.name,
                            "superficie": "tool_call"})
    anotar(tool_context.state, v, tool_context.invocation_id)
    return BLOQUEO_ENTRADA if v and v["bloqueado"] else None


async def revisar_resultado(tool, args, tool_context, tool_response):
    """after_tool_callback. Que devolvio la herramienta.

    Se manda la llamada y su respuesta juntas, ligadas por tool_call_id:
    asi la respuesta se evalua en la superficie Tool Response y con el
    contexto de que la pidio. Es el punto donde se corta la inyeccion
    indirecta, la que no viene del teclado del usuario sino del documento
    que la herramienta recupero.
    """
    mensajes = [_llamada(tool.name, args),
                {"role": "tool", "tool_call_id": "c1",
                 "content": _legible(tool_response)[:TOPE]}]
    v = await evaluar(mensajes, punto="2",
                      meta={**contexto(tool_context), "herramienta": tool.name,
                            "superficie": "tool_response"})
    anotar(tool_context.state, v, tool_context.invocation_id)
    return BLOQUEO_SALIDA if v and v["bloqueado"] else None
