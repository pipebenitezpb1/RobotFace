#!/bin/zsh
# Doble clic para que los ojos sigan tu cara con la cámara (Ctrl+C para detener)
cd "$(dirname "$0")"
# Cierra lo que haya quedado abierto antes (si no, dos programas pelean por la cámara o el Arduino)
pkill -9 -f "[s]eguir.py" 2>/dev/null; sleep 0.5
.venv/bin/python -u seguir.py --ventana 2>&1 | grep --line-buffered -v -E "WARN|W0000|I0000|XNNPACK|inference_feedback" | tee registro_seguir.txt
