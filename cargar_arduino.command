#!/bin/zsh
# Doble clic: busca el Arduino, le carga OjosAnimados y abre los ojos y la conversación
cd "$(dirname "$0")"
ARDUINO=~/.local/bin/arduino-cli
PUERTO=$($ARDUINO board list | grep -o '/dev/cu.usb[^ ]*' | head -1)
if [ -z "$PUERTO" ]; then
  echo "No encuentro el Arduino. Revisa el cable USB y vuelve a intentar."
  exit 1
fi
echo "Arduino en $PUERTO, cargando el programa..."
pkill -f seguir.py; pkill -f hablar.py; sleep 1
$ARDUINO compile --fqbn arduino:avr:uno -u -p "$PUERTO" OjosAnimados || exit 1
echo "Listo. Abriendo los ojos y la conversación..."
open -a Terminal seguir.command
sleep 8
open -a Terminal hablar.command
