# Agente bancario on-premise con Check Point AI Guardrails

Un asistente bancario de cinco agentes ADK (orquestador + cuentas, fraude, tarjetas y
conocimiento) con memoria por cliente, en Docker Compose sobre Debian o Ubuntu.
Check Point AI Guardrails bloquea los ataques en cuatro puntos:

| Punto | Que inspecciona | Donde |
|---|---|---|
| 1 | El mensaje del cliente, antes del agente | `puente/main.py` |
| 2 | Delegacion entre agentes, herramientas y `recordar()` | `agente/bank_agents/shared/protec_tools.py` |
| 3 | El turno antes de guardarlo en la memoria | `agente/bank_agents/memoria.py` |
| 4 | La pregunta y la respuesta, antes de mostrarla | `puente/main.py` |

## Uso

```bash
git clone --depth 1 --branch v1.1 https://github.com/luisbalbuenabl-stack/banca-guardrails-checkpoint.git ~/banca-guardrails-checkpoint
cd ~/banca-guardrails-checkpoint
make token        # crea el .env
nano .env         # LLM_PROVIDER, la API key del modelo y las de AI Guardrails
make modelos      # nombres validos para MODEL_*
make up           # levanta db, agente y puente
make humo         # comprueba el laboratorio
make consola      # URL y token de la consola
```

El paso a paso completo esta en la guia HTML del laboratorio.

Las claves van solo en el `.env` (permisos 600, fuera de git). Los agentes usan a
proposito un perfil vulnerable y documentos con texto inyectado: es un laboratorio
con datos ficticios, no para produccion.
