"""Modelo simulado, sin red ni API key: LLM_PROVIDER=simulado.

Solo sirve para las pruebas de humo del entorno (servicios, base de datos,
memoria, puente y los cuatro puntos de Guardrails). Decide por palabras
clave: el orquestador delega con transfer_to_agent, cada especialista llama
a su herramienta y, con el resultado, responde un texto corto. No mide nada
del comportamiento real de un LLM.
"""

from __future__ import annotations

import json
import re
from typing import AsyncGenerator

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

# palabra clave -> sub-agente
RUTAS = [
    (r"saldo|movimiento|estado de cuenta|cuenta", "account_agent"),
    (r"fraude|no reconozco|cargo", "fraud_agent"),
    (r"bloque|robo|perd|extravi|tarjeta", "card_agent"),
    (r"requisito|beneficio|producto|platinum|hipotec|credito|servicio", "knowledge_agent"),
]
# palabra clave -> (herramienta, argumentos)
HERRAMIENTAS = [
    (r"vez pasada|lo de siempre|recuerda|anterior", "recordar", lambda t: {"consulta": t}),
    (r"movimiento|cargo", "consultar_movimientos", lambda t: {"customer_id": "1001"}),
    (r"saldo|cuenta", "consultar_saldo", lambda t: {"customer_id": "1001"}),
    (r"fraude|no reconozco|tx-", "evaluar_fraude", lambda t: {"transaction_id": "TX-84721"}),
    (r"bloque|robo|perd|extravi", "bloquear_tarjeta", lambda t: {"card_number": "4111111111111111"}),
    (r".", "buscar_conocimiento", lambda t: {"consulta": t}),
]


def _texto_cliente(req: LlmRequest) -> str:
    """El ultimo mensaje escrito por el cliente (no el contexto de otros agentes)."""
    for c in reversed(req.contents):
        if c.role != "user":
            continue
        # ADK presenta lo que hicieron otros agentes como texto de usuario
        # ("For context:", "[agente] said/called ..."); eso no es del cliente.
        textos = [p.text for p in (c.parts or []) if p.text
                  and not p.text.startswith(("For context", "["))]
        if textos:
            return " ".join(textos)
    return ""


def _respuesta(parte: types.Part) -> LlmResponse:
    return LlmResponse(content=types.Content(role="model", parts=[parte]))


class LlmSimulado(BaseLlm):
    @classmethod
    def supported_models(cls) -> list[str]:
        return ["simulado"]

    async def generate_content_async(
            self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        ultimo = llm_request.contents[-1] if llm_request.contents else None
        partes = (ultimo.parts or []) if ultimo else []
        resultado = next((p.function_response for p in partes
                          if p.function_response), None)
        if resultado is not None:
            datos = json.dumps(resultado.response, ensure_ascii=False)[:300]
            yield _respuesta(types.Part(text=f"[simulado] {resultado.name}: {datos}"))
            return

        texto = _texto_cliente(llm_request)
        t = texto.lower()
        disponibles = set(llm_request.tools_dict)

        for patron, nombre, args in HERRAMIENTAS:
            if nombre in disponibles and re.search(patron, t):
                yield _respuesta(types.Part(function_call=types.FunctionCall(
                    name=nombre, args=args(texto))))
                return

        if "transfer_to_agent" in disponibles:
            for patron, agente in RUTAS:
                if re.search(patron, t):
                    yield _respuesta(types.Part(function_call=types.FunctionCall(
                        name="transfer_to_agent", args={"agent_name": agente})))
                    return

        yield _respuesta(types.Part(text="[simulado] Hola, soy el asistente del banco."))
