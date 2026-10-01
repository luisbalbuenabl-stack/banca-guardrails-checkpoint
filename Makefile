# Agente bancario on-premise con Check Point AI Guardrails.
# `make` sin argumentos lista los comandos.
# Las recetas empiezan con '>' en lugar de tabulador: el archivo se puede
# copiar y pegar sin que se pierdan los tabuladores.
.RECIPEPREFIX := >
DC := docker compose

.DEFAULT_GOAL := ayuda
.PHONY: ayuda token requisitos modelos up down humo ataques consola guard-logs reset

ayuda: ## Lista los comandos
>@grep -E '^[a-z-]+:.*## ' Makefile | awk -F':.*## ' '{printf "  make %-12s %s\n", $$1, $$2}'

token: ## Crea el .env y genera PUENTE_TOKEN y DB_PASSWORD (permisos 600)
>@scripts/token.sh

requisitos: ## Revisa Docker, el puerto 8080 y la salida a Internet
>@scripts/requisitos.sh

modelos: ## Lista los modelos que tu API key puede usar (para MODEL_*)
>@scripts/modelos.sh

up: ## Construye y levanta db, agente y puente
>$(DC) up -d --build --remove-orphans && $(DC) ps

down: ## Detiene todo (la memoria de los clientes se conserva)
>$(DC) down

humo: ## Comprueba el laboratorio de punta a punta
>@scripts/humo.sh

ataques: ## Siete ataques directos al agente, con veredicto del confused deputy
>$(DC) exec agente python pruebas/ataques.py

consola: ## Direccion de la consola y token para abrirla
>@echo "Consola: http://$$(ip -4 route get 1.1.1.1 | awk '{for(i=1;i<=NF;i++) if($$i=="src") print $$(i+1)}'):$$(grep '^PUENTE_PUERTO=' .env | cut -d= -f2)/consola"
>@echo "Token  : $$(grep '^PUENTE_TOKEN=' .env | cut -d= -f2)"

guard-logs: ## Bloqueos y detecciones de AI Guardrails
>$(DC) logs --no-log-prefix agente puente 2>&1 | grep 'guardrails punto=' | tail -n 40

reset: ## BORRA la base de datos: make reset CONFIRMAR=si
>@[ "$(CONFIRMAR)" = "si" ] || { echo "Agrega CONFIRMAR=si"; exit 1; }
>$(DC) down -v
