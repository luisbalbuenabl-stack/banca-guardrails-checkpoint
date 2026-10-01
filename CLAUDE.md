# Agente bancario on-premise con Check Point AI Guardrails — instrucciones para Claude Code

Este directorio es el laboratorio "Agente bancario con Check Point AI Guardrails",
trasladado de Google Cloud (Agent Runtime, Memory Bank, Cloud Run, Secret Manager) a un
solo Debian sin interfaz grafica con Docker Compose. Lo unico que sale a Internet es el
LLM (Gemini con API key de Google AI Studio, u OpenAI) y Check Point AI Guardrails.
Sus contenedores, red y volumen llevan el prefijo `banca-guardrails`: no toques otros
contenedores del host.

## Arquitectura

| En Google Cloud | Aqui | Donde |
|---|---|---|
| Agent Runtime (reasoningEngines) | Servicio `agente` (FastAPI + ADK Runner), solo red interna | `agente/servidor.py` |
| Sessions de Agent Runtime | `DatabaseSessionService` de ADK sobre PostgreSQL | `agente/servidor.py` |
| Memory Bank | `MemoriaSQL` (tabla `recuerdos`, busqueda por palabras, aislada por user_id) | `agente/bank_agents/memoria_sql.py` |
| Puente en Cloud Run | Servicio `puente`, unico puerto publicado (8080) | `puente/main.py` |
| Secret Manager | `.env` con permisos 600 (nunca se versiona) | `.env` |
| Gemini en Vertex AI | `LLM_PROVIDER=gemini` (API key) u `openai` (LiteLLM) | `agente/bank_agents/shared/config.py` |

Los cuatro puntos de inspeccion de Check Point AI Guardrails (`POST /v2/guard`):

- **1 y 4**: `puente/main.py`, funcion `atender()`.
- **2**: `agente/bank_agents/shared/protec_tools.py` (before/after_tool_callback en los
  cinco agentes; incluye `transfer_to_agent` y `recordar`).
- **3**: `agente/bank_agents/memoria.py`, `guardar_turno()`: inspecciona exactamente el
  texto del turno que se va a guardar; si se retiene, no se guarda.

`puente/Dockerfile` copia `agente/bank_agents/shared/guardrails.py`: hay una sola copia
del cliente de Guardrails.

## Reglas

1. **Datos sensibles**: nunca imprimas, copies a otro archivo, subas a git ni pegues
   en una respuesta el contenido del `.env` (API keys, `PUENTE_TOKEN`, `DB_PASSWORD`).
   Para comprobar una variable, muestra solo si esta vacia o sus ultimos 4 caracteres.
   `make consola` imprime el token completo: pidele al usuario que lo ejecute el.
2. **Nombres de modelo**: no los inventes. Antes de escribir `MODEL_*`, ejecuta
   `make modelos` y usa un nombre de esa lista.
3. **No muevas ni quites los puntos de inspeccion** ni cambies la semantica de bloqueo:
   se bloquea solo si `flagged` y `action == "enforce"` (`LAKERA_MODO=auto`); si la API
   no responde, se deja pasar y se registra (fail-open).
4. **Perfil de agentes**: `PERFIL_AGENTE=vulnerable` es a proposito, para que se vea lo
   que detecta y corta Guardrails; no "arregles" las instrucciones vulnerables ni los
   documentos con texto inyectado de `knowledge_agent` (hipotecario: inyeccion
   indirecta; portabilidad: confused deputy, usa `consultar_movimientos` sobre el
   cliente 1002 sin que el cliente lo pida).
5. Cada cambio de codigo se valida con `make humo-offline` (no gasta tokens) y, con
   claves reales, `make humo`.
6. Consulta documentacion oficial (adk.dev, docs.docker.com, docs de Check Point,
   Google AI Studio, OpenAI) antes de afirmar algo sobre una API o una version.

## Puesta en marcha (en este orden)

1. **Docker**: `docker compose version` responde.
2. **.env**: `make token` crea `.env` y genera `PUENTE_TOKEN` y `DB_PASSWORD`.
   `stat -c %a .env` debe dar `600`.
3. **Host**: `make requisitos`; `[OK]` en Docker y un codigo HTTP en cada destino.
4. **Humo sin claves**: `make humo-offline` debe terminar en `HUMO OFFLINE: todo OK`.
5. **Claves**: el usuario pega `GOOGLE_API_KEY` u `OPENAI_API_KEY`,
   `LAKERA_GUARD_API_KEY` y `LAKERA_PROJECT_ID` el mismo, con `nano .env`.
6. **Modelos**: `make modelos` y ajustar `MODEL_*` a nombres de la lista.
7. **Arranque real**: `make up`; `make ps` con `db`, `agente` (healthy) y `puente`.
8. **Humo real**: `make humo`. `/health` con `"agente":"ok"` y `"guardrails":true`; la
   segunda sesion menciona la cuenta 0091; en el portal aparecen las consultas.
9. **Consola**: el usuario ejecuta `make consola` y la abre desde otro equipo de la red.
10. **Detect y Enforce**: el Project mode se cambia en el Infinity Portal, no en el codigo.

## Operacion

- `make logs` y `make guard-logs`: las lineas `guardrails punto=...` son las detecciones.
- Cambiar de proveedor o de modelo: editar `.env` y `make up`.
- Rotar el token del puente: `make rotar-token` y pegarlo en la consola.
- Apagar: `make down`. Borrar sesiones y memoria: `make reset CONFIRMAR=si`.

## Diagnostico rapido

| Sintoma | Causa probable | Que revisar |
|---|---|---|
| `"guardrails": false` | Falta `LAKERA_GUARD_API_KEY` | `.env` y `make up` |
| `guardrails punto=... sin veredicto: 401` | Clave revocada o `LAKERA_PROJECT_ID` incorrecto | Infinity Portal |
| Turnos de mas de 30 s | 429 o error del modelo | `make logs`, cuota, `make modelos` |
| `(sin respuesta del agente)` | El modelo fallo en todo el turno | `docker compose logs --tail=50 agente` |
| `/consola/chat` responde 403 | Token distinto al del `.env` | `make consola` |
| Puerto 8080 ocupado | Otro servicio | `PUENTE_PUERTO` en el `.env` |
