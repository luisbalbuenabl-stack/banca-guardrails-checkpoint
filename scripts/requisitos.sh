#!/usr/bin/env bash
# Revision de requisitos del host (cualquier distribucion Linux). Solo lee; no instala nada.
ok()  { printf "  [OK]    %s\n" "$1"; }
mal() { printf "  [FALTA] %s\n" "$1"; }
ojo() { printf "  [OJO]   %s\n" "$1"; }

echo "== Sistema"
. /etc/os-release 2>/dev/null
ok "${PRETTY_NAME:-Linux} (kernel $(uname -r))"
ARQ=$(uname -m)
case "$ARQ" in x86_64|aarch64) ok "arquitectura $ARQ" ;; *) mal "arquitectura $ARQ (se necesita x86_64 o aarch64)" ;; esac
CPU=$(nproc); [ "$CPU" -ge 2 ] && ok "$CPU CPU" || ojo "$CPU CPU (recomendado 2 o mas)"
# Una VM de 4 GB reporta algo menos (el kernel reserva una parte): se acepta desde 3500 MB.
RAM=$(awk '/MemTotal/ {printf "%d", $2/1024}' /proc/meminfo)
[ "$RAM" -ge 3500 ] && ok "${RAM} MB de RAM" || ojo "${RAM} MB de RAM (recomendado 4 GB)"
DISCO=$(df -BG --output=avail "$HOME" | tail -1 | tr -dc 0-9)
[ "$DISCO" -ge 10 ] && ok "${DISCO} GB libres en $HOME" || ojo "${DISCO} GB libres (recomendado 10 o mas)"
timedatectl show -p NTPSynchronized --value 2>/dev/null | grep -q yes \
  && ok "hora sincronizada (NTP)" || ojo "no se pudo confirmar la sincronizacion de hora (NTP)"
command -v getenforce >/dev/null && ok "SELinux: $(getenforce)"

echo "== Herramientas"
for h in curl openssl make tar python3; do
  command -v $h >/dev/null && ok "$h" || mal "$h   (instalalo con el gestor de paquetes de tu distribucion)"
done
command -v ip >/dev/null && command -v ss >/dev/null && ok "ip y ss" || mal "ip y ss   (paquete iproute2, o iproute en RHEL/Fedora)"
sudo -n true 2>/dev/null && ok "sudo disponible" \
  || { groups | grep -qwE "sudo|wheel" && ok "usuario en el grupo sudo/wheel" || ojo "sin sudo: hara falta para instalar Docker"; }

echo "== Docker"
if command -v docker >/dev/null; then
  ok "$(docker --version)"
  docker compose version >/dev/null 2>&1 && ok "$(docker compose version)" || mal "plugin docker compose"
  docker info >/dev/null 2>&1 && ok "el usuario puede usar Docker sin sudo" \
    || ojo "docker info falla: servicio parado o el usuario no esta en el grupo docker"
else
  mal "Docker Engine (instalacion oficial por distribucion: docs.docker.com/engine/install/)"
fi

echo "== Puerto del puente"
P=$(grep -s '^PUENTE_PUERTO=' .env | cut -d= -f2); P=${P:-8080}
if ss -ltn 2>/dev/null | awk '{print $4}' | grep -q ":$P\$"; then
  docker ps --format '{{.Names}} {{.Ports}}' 2>/dev/null | grep -q "^banca-guardrails-puente.*:$P->" \
    && ok "$P en uso por el puente de este laboratorio" || ojo "el $P lo usa otro servicio: cambia PUENTE_PUERTO en el .env"
else ok "$P libre"; fi

echo "== Proxy"
[ -n "${https_proxy:-${HTTPS_PROXY:-}}" ] && ojo "hay proxy HTTPS configurado: Docker lo necesita aparte" || ok "sin proxy"

echo "== Salida a Internet (cualquier codigo HTTP = hay ruta; 000 = bloqueado)"
for u in https://download.docker.com https://registry-1.docker.io/v2/ https://pypi.org/simple/ \
         https://github.com https://generativelanguage.googleapis.com https://api.openai.com \
         https://api.lakera.ai; do
  c=$(curl -s -o /dev/null -m 10 -w '%{http_code}' "$u")
  [ "$c" = "000" ] && mal "$u -> sin ruta" || ok "$u -> $c"
done
