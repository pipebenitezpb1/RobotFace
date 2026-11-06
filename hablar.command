#!/bin/zsh
# Doble clic para conversar con el robot (Esc en la ventana de la boca para salir)
cd "$(dirname "$0")"
# Cierra lo que haya quedado abierto antes (si no, dos programas pelean por la cámara o el Arduino)
pkill -9 -f "[h]ablar.py" 2>/dev/null; sleep 0.5
.venv/bin/python -u hablar.py 2>&1 | tee registro_hablar.txt
