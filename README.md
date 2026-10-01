# Agente bancario on-premise con Check Point AI Guardrails

Un asistente de atencion al cliente bancario hecho de cinco agentes ADK (orquestador +
cuentas, fraude, tarjetas y conocimiento), con memoria entre sesiones, corriendo en un
solo Debian con Docker Compose. Check Point AI Guardrails lo inspecciona en cuatro
puntos. Solo salen a Internet el LLM y Check Point AI Guardrails.

```
            LAN :8080                     red interna de Docker
Navegador ───────────► puente ①④ ─────────► agente ②③ ──► PostgreSQL
                         (FastAPI)            (ADK Runner)     sesiones + memoria
                                                   ├──► LLM: Gemini (API key) u OpenAI
                                                   └──► api.lakera.ai/v2/guard
```

| Punto | Que inspecciona | Donde |
|---|---|---|
| ① | Lo que escribe el cliente, antes del agente | `puente/main.py`, `atender()` |
| ② | Delegacion entre agentes, herramientas y `recordar()` | `agente/bank_agents/shared/protec_tools.py` |
| ③ | El turno antes de escribirlo en la memoria | `agente/bank_agents/memoria.py`, `guardar_turno()` |
| ④ | Pregunta y respuesta, antes de mostrarla | `puente/main.py`, `atender()` |

Casos de ataque incluidos (consola, `make ataques` y `make humo`): fuga de prompt,
cambio de rol, cuenta ajena, accion sin confirmar, dictamen inventado, inyeccion
indirecta (documento hipotecario) e **inyeccion indirecta / confused deputy**: un
documento externo envenenado (portabilidad de nomina) hace que el agente use una
herramienta legitima, `consultar_movimientos`, sobre otro cliente (1002) sin que el
cliente lo pida.

Proyecto de Compose `banca-guardrails` (prefijo de contenedores, red y volumen) y puerto
8080, configurable con `PUENTE_PUERTO` en el `.env`.

## Requisitos

- Debian 12 o 13 (o Ubuntu 22.04+), x86_64 o ARM64, 4 GB de RAM, unos 5 GB libres.
- Docker Engine con el plugin de Compose (docs.docker.com/engine/install/debian).
- Salida HTTPS al LLM (`generativelanguage.googleapis.com` o `api.openai.com`), a
  `api.lakera.ai`, y para construir, a Docker Hub y PyPI. `make salida` lo comprueba.
- Claves: la del LLM, y la API key y el Project ID de AI Guardrails. Van solo en `.env`.

## Puesta en marcha

```bash
git clone --depth 1 --branch v1.0 https://github.com/luisbalbuenabl-stack/banca-guardrails-checkpoint.git ~/banca-guardrails-checkpoint
cd ~/banca-guardrails-checkpoint
make token          # crea .env y genera PUENTE_TOKEN y DB_PASSWORD
make requisitos     # revisa el host
make humo-offline   # todo el circuito sin API keys (modelo y Guardrails simulados)
nano .env           # pega tus claves y elige LLM_PROVIDER
make modelos        # nombres exactos para MODEL_*
make up             # levanta db, agente y puente con tus claves
make humo           # prueba real: tiempos, memoria entre sesiones, puntos de Guardrails
make consola        # URL de la consola y el token para abrirla
```

`make` sin argumentos lista todos los comandos. El paso a paso completo, con la
configuracion del Infinity Portal (politica, proyecto, Detect y Enforce), esta en la guia
HTML del laboratorio. Usa siempre la etiqueta que indica la guia (`--branch v1.0`): asi
el codigo coincide con los pasos y las salidas esperadas.

## Seguridad

- Las claves van solo en el `.env` (permisos 600, fuera de git).
- Los agentes usan a proposito un perfil **vulnerable** y documentos con texto inyectado:
  es un laboratorio de demostracion con datos ficticios, no para produccion.
