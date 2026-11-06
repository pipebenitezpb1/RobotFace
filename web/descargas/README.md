# RobotFace: Claude físico y expresivo

Proyecto de **Diseño de Interfaces**, Universidad Adolfo Ibáñez, 2026.

Unos ojos animatrónicos sobre la pantalla de un MacBook que miran a quien habla, conversan por voz con Claude y muestran emociones con los párpados y con una boca animada en la pantalla. La interfaz no es una pantalla con botones: es una mirada, un gesto y una voz.

La página de la entrega se abre con `pagina.command`, en http://localhost:8730. Desde su **panel en vivo** se enciende y apaga el robot, y se ven la boca, la cámara con las caras, los subtítulos y la conversación. También tiene botones de expresiones y para escanear caras. Solo funciona en el Chrome de este Mac.

## Qué hace

- **Mira.** Sigue las caras con la cámara del Mac y apunta a los ojos de la persona. Si hay varias, mira a la que mueve la boca.
- **Conversa.**
  - Escucha con Whisper, que corre en el Mac.
  - Responde con Claude (Haiku 5.5) y habla con la voz de macOS.
  - Mueve la boca en pantalla al ritmo del audio.
  - Se calla si lo interrumpen.
- **Expresa.** Tiene 16 expresiones de ojos (sorpresa, sospecha, guiño, pensar, triste, confundido, dormido, despertar…) y bocas según la emoción. Claude elige la expresión de cada frase.
- **Duerme y despierta.**
  - A los 10 s sin ver a nadie, cierra los ojos y ronca en pantalla.
  - Solo lo despierta ver a alguien, nunca el ruido.
  - Al despertar, abre los ojos mirando a la persona y la saluda.
- **Reconoce, con permiso.**
  - Combina la cara (SFace) y la ropa en una sola nota.
  - Botón **Escanear cara**: guía a la persona por voz en 6 ángulos.
  - Todo queda guardado solo en este computador y se puede olvidar cuando la persona lo pida.

## Hardware

| Parte | Detalle |
|---|---|
| Mecanismo | EyeMech ε3.2 de Will Cogley, impreso en PLA |
| Servos | 6 × SG90: 4 para los párpados, 2 para la mirada (X e Y) |
| Control | Arduino UNO + PCA9685 (I2C 0x40; SDA→A4, SCL→A5) |
| Energía de los servos | 5 V por un módulo USB-C, en una cápsula impresa |
| Montura | Base de acrílico de 5 mm, ganchos fijos a 15° sobre la pantalla y pata con varilla M8 hasta la mesa |
| Electrónica | Caja de MDF de 3 mm con grabado de cerebro |

## Programas

| Archivo | Qué hace |
|---|---|
| `OjosAnimados/OjosAnimados.ino` | Ojos en el Arduino: mirada, parpadeo sincronizado y expresiones. Recibe `M x y`, `E n` y `D` por serie a 115200 |
| `seguir.py` / `seguir.command` | Cámara: detecta caras (YuNet), ve quién habla (MediaPipe), reconoce (SFace + ropa), duerme y despierta, y tiene el escaneo de caras |
| `hablar.py` / `hablar.command` | Voz: Whisper, Claude, voz Paulina y boca en pantalla (pygame) |
| `cabeza/*.py` | Modelos 3D y cortes láser (CadQuery) |
| `servidor.py` / `pagina.command` | Servidor local de la página: enciende y apaga el robot, y pasa la boca y la cámara en vivo al panel |
| `web/` | Página de la entrega (`web/armar.py` arma las imágenes y descargas) |

`seguir.py` y `hablar.py` se comunican por UDP (puertos 47800 y 47801) y con archivos de aviso (`durmiendo`, `saludar`, `decir`, `escaneando`).

## Instalación (macOS con Apple Silicon)

```bash
uv venv .venv --python 3.12 && uv pip install -p .venv -r requisitos.txt
./descargar_modelos.sh
echo "sk-ant-..." > clave_anthropic.txt   # tu clave de la API de Anthropic (no se sube)
```

Para cargar el Arduino, usa `cargar_arduino.command`. Necesita `arduino-cli` en `~/.local/bin`.

Para usarlo, abre `seguir.command` y después `hablar.command`. Cada uno cierra solo la copia anterior que haya quedado abierta.

**Teclas en la ventana de la cámara:**
- **Escanear cara** (botón) o **R**: registra una cara con permiso de la persona.
- **1–9**: expresiones.
- **w** / **s**: suben o bajan la mirada.
- **q**: salir.

**Teclas en la ventana de la boca:**
- **F**: pantalla completa.
- **M**: silenciar.
- **S**: subtítulos.
- **U**: deslizable del umbral de voz.
- **Esc**: salir.

## Privacidad

Las caras son datos biométricos:
- Solo se guardan si la persona dice que sí.
- Quedan solo en este computador (`caras_conocidas.json`, `personas.json`).
- Se borran cuando la persona pide que la olviden.

Ninguno de esos archivos, ni la clave de la API, entra al repositorio (ver `.gitignore`).

## Créditos

- Mecanismo de ojos: [EyeMech ε3.2](https://github.com/will-cogley/EyeMech_Epsilon), de Will Cogley.
- Conversación: Claude, de Anthropic.
- Visión: OpenCV (YuNet, SFace) y MediaPipe.
- Voz a texto: Whisper (MLX).
