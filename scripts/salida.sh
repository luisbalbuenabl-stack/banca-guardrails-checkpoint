#!/usr/bin/env bash
# Comprueba la salida a Internet que necesita el laboratorio (sin enviar datos).
# Cualquier codigo HTTP (200, 401, 404...) significa que hay ruta; 000 = bloqueado.
cd "$(dirname "$0")/.."
set -a; [ -f .env ] && . ./.env; set +a
probar() { printf "%-48s %s\n" "$1" "$(curl -s -o /dev/null -m 10 -w '%{http_code}' "$1")"; }
echo "== LLM (${LLM_PROVIDER:-gemini})"
[ "${LLM_PROVIDER:-gemini}" = "openai" ] && probar https://api.openai.com/v1/models \
  || probar https://generativelanguage.googleapis.com/v1beta/models
echo "== Check Point AI Guardrails";  probar https://api.lakera.ai/v2/guard
echo "== Imagenes y paquetes (solo para construir)"
probar https://registry-1.docker.io/v2/; probar https://pypi.org/simple/
