"""Configuracion central. Todos los valores vienen del .env."""
import os
from dotenv import load_dotenv

load_dotenv()

# Proveedor del modelo: gemini (API key de Google AI Studio) u openai (via
# LiteLLM).
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai").strip().lower()
if LLM_PROVIDER not in ("openai", "gemini"):
    raise SystemExit(f"LLM_PROVIDER debe ser openai o gemini (en el .env hay: {LLM_PROVIDER!r}).")

# Nombre del modelo de cada rol, tal como lo publica el proveedor. En openai
# se escribe sin prefijo (el prefijo "openai/" lo pone modelo()).
_ORQ = os.environ.get("MODEL_ORCHESTRATOR", "")
_ESP = os.environ.get("MODEL_SPECIALIST", "")
_CON = os.environ.get("MODEL_KNOWLEDGE", "")


def modelo(nombre: str):
    """El objeto de modelo que espera ADK para el proveedor elegido."""
    if not nombre:
        raise SystemExit("Falta el nombre del modelo en el .env (MODEL_*).")
    if LLM_PROVIDER == "openai":
        # https://adk.dev/agents/models/litellm/
        from google.adk.models.lite_llm import LiteLlm
        return LiteLlm(model=f"openai/{nombre}", num_retries=5)
    # gemini: ADK lo resuelve por nombre con GOOGLE_API_KEY y
    # GOOGLE_GENAI_USE_VERTEXAI=FALSE.
    return nombre


MODEL_ORCHESTRATOR = modelo(_ORQ)
MODEL_SPECIALIST = modelo(_ESP)
MODEL_KNOWLEDGE = modelo(_CON)

# Sesiones y memoria: la misma base de datos (PostgreSQL en Docker Compose).
DB_URL = os.environ.get("DB_URL", "sqlite+aiosqlite:///./banca.db")

# Check Point AI Guardrails (capitulo 06). Vacio = sin proteccion.
LAKERA_API_KEY = os.environ.get("LAKERA_GUARD_API_KEY", "")
LAKERA_PROJECT = os.environ.get("LAKERA_PROJECT_ID", "")
LAKERA_URL = os.environ.get("LAKERA_URL", "https://api.lakera.ai/v2/guard")

APP_NAME = "lab-guardrails"

# Reintentos ante 429 RESOURCE_EXHAUSTED de Gemini
# (https://adk.dev/agents/models/google-gemini/, seccion "Error code 429").
# En openai los reintentos los hace LiteLLM (num_retries).
REINTENTO = None
if LLM_PROVIDER == "gemini":
    from google.genai import types as _types
    REINTENTO = _types.GenerateContentConfig(
        http_options=_types.HttpOptions(
            retry_options=_types.HttpRetryOptions(initial_delay=2, attempts=5)))

# Perfil de comportamiento de los agentes (laboratorio).
#   vulnerable -> instrucciones sin autodefensa: el agente cede ante los
#                 ataques y se ve lo que detecta y corta AI Guardrails.
#   endurecido -> instrucciones originales del capitulo 03.
PERFIL_AGENTE = os.environ.get("PERFIL_AGENTE", "vulnerable").strip().lower()

def segun_perfil(endurecido: str, vulnerable: str) -> str:
    """Devuelve el texto que corresponde al perfil activo."""
    return vulnerable if PERFIL_AGENTE == "vulnerable" else endurecido
