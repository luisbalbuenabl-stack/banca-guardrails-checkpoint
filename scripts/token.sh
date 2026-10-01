#!/usr/bin/env bash
# Genera PUENTE_TOKEN y DB_PASSWORD si estan vacios, y deja el .env en modo 600.
# Con "rotar" genera un PUENTE_TOKEN nuevo aunque ya exista.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] || cp .env.example .env
poner() {  # poner VARIABLE VALOR
  if grep -q "^$1=" .env; then sed -i "s|^$1=.*|$1=$2|" .env; else echo "$1=$2" >> .env; fi
}
vacio() { [ -z "$(grep "^$1=" .env | cut -d= -f2-)" ]; }
if vacio PUENTE_TOKEN || [ "${1:-}" = "rotar" ]; then poner PUENTE_TOKEN "$(openssl rand -hex 32)"; echo "PUENTE_TOKEN generado"; fi
if vacio DB_PASSWORD; then poner DB_PASSWORD "$(openssl rand -hex 24)"; echo "DB_PASSWORD generado"; fi
chmod 600 .env
echo "Token del puente (termina en): ...$(grep '^PUENTE_TOKEN=' .env | cut -d= -f2 | tail -c 5)"
