#!/bin/zsh
# Igual que seguir.command, pero guarda las medidas de las bocas para calibrar
cd "$(dirname "$0")"
.venv/bin/python -u seguir.py --ventana --calibrar 2> >(grep -v -E "WARN|W0000|I0000|XNNPACK|inference_feedback" >&2)
