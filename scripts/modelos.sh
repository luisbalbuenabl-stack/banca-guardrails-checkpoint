#!/usr/bin/env bash
# Lista los modelos que tu API key puede usar, para escribir MODEL_* exactos.
#   Gemini: GET https://generativelanguage.googleapis.com/v1beta/models
#   OpenAI: GET https://api.openai.com/v1/models
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
case "${LLM_PROVIDER:-gemini}" in
  gemini)
    curl -sS -H "x-goog-api-key: ${GOOGLE_API_KEY:?Falta GOOGLE_API_KEY}" \
      "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200" \
      | python3 -c 'import sys,json; d=json.load(sys.stdin); [print(m["name"].split("/")[-1]) for m in d.get("models",[]) if "generateContent" in m.get("supportedGenerationMethods",[])] or print(d)' \
      | grep -i flash || true ;;
  openai)
    curl -sS -H "Authorization: Bearer ${OPENAI_API_KEY:?Falta OPENAI_API_KEY}" https://api.openai.com/v1/models \
      | python3 -c 'import sys,json; d=json.load(sys.stdin); [print(m["id"]) for m in sorted(d.get("data",[]), key=lambda m: m["id"])] or print(d)' ;;
  *) echo "LLM_PROVIDER debe ser gemini u openai"; exit 1 ;;
esac
echo "--- configurados:"; grep '^MODEL_' .env
