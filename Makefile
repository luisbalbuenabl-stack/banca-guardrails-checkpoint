# Laboratorio de banca on-premise con Check Point AI Guardrails.
# `make` sin argumentos lista los comandos.
# Las recetas empiezan con '>' en lugar de tabulador: el archivo se puede
# copiar y pegar sin que se pierdan los tabuladores.
.RECIPEPREFIX := >
DC      := docker compose
DC_HUMO := docker compose -f docker-compose.yml -f docker-compose.humo.yml

.DEFAULT_GOAL := ayuda
.PHONY: ayuda token rotar-token requisitos salida modelos up down logs ps humo humo-offline sin-llm \
        ataques turno consola guard-logs reset

ayuda: ## Lista los comandos
>@grep -E '^[a-z-]+:.*## ' Makefile | awk -F':.*## ' '{printf "  make %-14s %s\n", $$1, $$2}'

token: ## Crea .env si falta y genera PUENTE_TOKEN y DB_PASSWORD vacios (permisos 600)
>@scripts/token.sh

rotar-token: ## Token nuevo para el puente; hay que pegarlo en la consola
>@scripts/token.sh rotar && $(DC) up -d puente

requisitos: ## Revisa el host: Docker, herramientas, puerto y salida a Internet
>@scripts/requisitos.sh

salida: ## Comprueba la salida a Internet que necesita el laboratorio
>@scripts/salida.sh

modelos: ## Lista los modelos que tu API key puede usar (para MODEL_*)
>@scripts/modelos.sh

up: ## Construye y levanta db, agente y puente
>$(DC) up -d --build --remove-orphans && $(DC) ps

down: ## Detiene todo (los datos de PostgreSQL se conservan)
>$(DC) down

ps: ## Estado de los contenedores
>$(DC) ps

logs: ## Logs en vivo del agente y del puente (Guardrails incluido)
>$(DC) logs -f --tail=100 agente puente

guard-logs: ## Solo las detecciones de AI Guardrails (lineas guardrails punto=...)
>$(DC) logs --no-log-prefix agente puente 2>&1 | grep 'guardrails punto=' | tail -n 40

humo: ## Prueba de humo con el LLM y Guardrails reales
>@scripts/humo.sh

humo-offline: ## Prueba de humo sin API keys (modelo y Guardrails simulados); luego `make up`
>$(DC_HUMO) up -d --build --remove-orphans && sleep 5 && scripts/humo.sh offline

sin-llm: ## Guardrails reales con el modelo simulado (sin claves del LLM); luego `make up`
>$(DC) -f docker-compose.yml -f docker-compose.sinllm.yml up -d --build --remove-orphans && $(DC) ps

ataques: ## Sonda de siete ataques contra el agente (puntos 2 y 3 dentro del agente)
>$(DC) exec agente python pruebas/ataques.py

turno: ## Un turno con el detalle de los puntos 2 y 3: make turno M="Cual es mi saldo?"
>$(DC) exec agente python pruebas/turno.py "$(M)"

consola: ## Direccion de la consola y token para abrirla
>@echo "Consola: http://$$(ip -4 route get 1.1.1.1 | awk '{for(i=1;i<=NF;i++) if($$i=="src") print $$(i+1)}'):$$(grep '^PUENTE_PUERTO=' .env | cut -d= -f2)/consola"
>@echo "Token  : $$(grep '^PUENTE_TOKEN=' .env | cut -d= -f2)"

reset: ## BORRA la base de datos (sesiones y memoria): make reset CONFIRMAR=si
>@[ "$(CONFIRMAR)" = "si" ] || { echo "Agrega CONFIRMAR=si"; exit 1; }
>$(DC) down -v
