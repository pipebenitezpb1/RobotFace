#!/bin/zsh
# Doble clic: abre la página del robot en Chrome (http://localhost:8730). Desde ahí se enciende y apaga.
# Ctrl+C en esta ventana apaga la página (el robot sigue hasta que lo apagues desde la página).
cd "$(dirname "$0")"
pkill -f "[s]ervidor.py" 2>/dev/null; pkill -f "[h]ttp.server 8730" 2>/dev/null; sleep 0.5
(sleep 1.2; open -a "Google Chrome" http://localhost:8730/#panel) &
.venv/bin/python -u servidor.py
