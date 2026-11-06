# RobotFace: traspaso para GitHub y portafolio

> **Para el chat que sube a GitHub y arma el portafolio:** todo el proyecto está en `~/RobotFace`, en este mismo Mac. Este archivo explica qué es, cómo se hizo, qué se puede publicar, qué no, y el texto para el portafolio. Lee primero las secciones 5 y 6: ahí está lo que **nunca** se sube.

---

## 1. En una frase

**RobotFace, "Claude físico y expresivo"**: unos ojos animatrónicos sobre la pantalla de un MacBook. Miran a quien habla, conversan por voz con Claude y muestran emociones con los párpados y con una boca animada en la pantalla.

Proyecto de **Diseño de Interfaces**, Universidad Adolfo Ibáñez (DesignLab), 2026.
- Autor: Luis Felipe Benítez *(completar si hay más integrantes del equipo)*.
- Estética de la página: Insta3D.

## 2. Estado actual (5 nov 2026)

**Funciona:**
- Seguir caras con la cámara.
- Conversar por voz.
- Las 16 expresiones.
- Dormir a los 10 s sin ver a nadie y despertar al ver a alguien, con saludo.
- Parpadeo sincronizado.
- Bocas según la emoción.
- Reconocimiento con cara y ropa, con permiso de la persona.
- Escaneo guiado de caras.

**Página de entrega:**
- Corre en `http://localhost:8730`; se abre con `pagina.command`.
- Tiene un **panel en vivo**:
  - enciende y apaga el robot;
  - muestra la boca, la cámara con las caras, el estado, los subtítulos y la conversación;
  - tiene botones de expresiones y de escaneo.

**Fabricado:**
- Base de acrílico de 5 mm cortada.
- Piezas impresas en PLA naranjo.
- Caja de MDF de 3 mm con grabado de cerebro.

**Sin probar todavía:**
- Una conversación larga desde el panel con alguien al frente.
- El escaneo de caras iniciado desde la página.
- La pata a la mesa con varilla M8 (en la foto de prueba se usaron antenas telescópicas).
- La cápsula USB-C impresa: las medidas del módulo son estimadas.

## 3. El proceso de diseño (para contar en el portafolio)

### 3.1 Hacer que el hardware responda
- El mecanismo es el **EyeMech ε3.2 de Will Cogley**: 6 servos SG90, 4 para los párpados y 2 para la mirada X/Y. Lo controlan un **Arduino UNO** y una **PCA9685** (I2C).
- Los programas se cargan desde la terminal con `arduino-cli`.
- **Calibramos servo por servo con fotos.** Después de rearmarlo hubo que invertir los canales 3 y 4 y bajar la apertura de los párpados izquierdos, porque forzaban el mecanismo.
- **Problemas reales:**
  - un cable USB que era solo de carga;
  - desconexiones del USB;
  - la PCA9685 sin I2C hasta recablear SDA→A4 y SCL→A5;
  - servos sin alimentación.

### 3.2 Ojos vivos
- Mirada al azar, parpadeo, y párpados que acompañan la mirada para no chocar.
- Llegamos a **16 expresiones**: sorpresa, sueño, enojo, sospecha, guiño, curioso, feliz, rodar los ojos, mirar alrededor, pensar, triste, parpadeo, confundido, nervioso, dormido y despertar.
- **Regla de diseño:** los dos ojos parpadean siempre juntos. La asimetría queda solo para el guiño y los gestos que la necesitan; los parpadeos descoordinados se veían como una falla.

### 3.3 Mirar a las personas
- La cámara del Mac detecta caras con **YuNet** y mide quién mueve la boca con **MediaPipe**, para mirar a quien habla.
- Al principio miraba muy arriba. Se corrigió apuntando a los **ojos** de la persona en vez de al centro de la cara, con ganancia vertical y un ajuste fino (teclas W/S).

### 3.4 Conversar
- **Cadena de la voz:**
  - **Whisper**, en la GPU del Mac (MLX);
  - **Claude** (Haiku 5.5, por velocidad y costo, con caché de prompt);
  - **voz Paulina** de macOS;
  - **boca de caricatura** en pantalla, que se mueve con el audio.
- **Personalidad:** amigo chileno, sarcasmo cariñoso, respuestas cortas, honesto sobre ser una IA.
- **Para que se sienta natural:**
  - se calla si lo interrumpen (distingue tu voz del eco de la suya);
  - ignora voces del fondo si nadie frente a la cámara mueve la boca;
  - solo dice muletillas ("mmm, a ver…") cuando le hicieron una **pregunta**; antes las decía siempre y se sentía lento.
- **Emociones:** Claude pone una etiqueta a cada frase ([feliz], [sarcastico]…). Los ojos hacen la expresión justo al decirla y la boca cambia de forma.

### 3.5 El ciclo de vida
- **Duerme:** a los 10 s sin ver a nadie, cierra los ojos y ronca en pantalla con "zzz". El ruido **no** lo despierta; fue una decisión explícita, para que no reaccione a cualquier sonido de la sala.
- **Despierta:** solo al ver una cara. Entreabre los ojos, parpadea, los abre mirando a la persona y la **saluda** (por su nombre si la reconoce).

### 3.6 Conocer a las personas
- **Conocimiento de la escuela:** sabe quiénes son las autoridades y profesores del DesignLab, según la página pública de la UAI, y saluda a los que se presentan.
- **Reconocimiento facial con consentimiento:**
  - antes de guardar una cara pregunta por voz;
  - la huella (SFace, 128 números) queda solo en el Mac;
  - "olvídame" la borra.
- **Escaneo guiado:** un botón, el nombre, y el robot guía por voz 6 ángulos (frente, izquierda, derecha, barbilla arriba y abajo, frente), con un marco que barre la cara.
- **Cara + ropa juntas:**
  - la cara pesa 70 % y la ropa 30 %, y la nota se suaviza en el tiempo;
  - la ropa ayuda cuando la cara se ve de lado o lejos;
  - una cara claramente distinta le gana a una ropa parecida.

### 3.7 La montura: iteraciones (la parte más de diseño industrial)

1. **Cabeza completa tipo personaje** → descartada: tapaba demasiado y era una copia de un personaje existente.
2. **Montura tipo cámara web, con pinza articulada y carcasa** → descartada: la articulación no aguantaba el peso.
3. **Frente de MDF que tapaba el mecanismo**, con una abertura por ojo y otra para el soporte central → **cortado y probado**, pero chocaba con los párpados al cerrar y con la pieza superior al mirar abajo (foto `estudio_frente_mdf.jpg`).
4. **Decisión final: el mecanismo queda a la vista.**
   - Base de **acrílico negro de 5 mm** cortada en láser, con ranuras.
   - **Ganchos fijos a 15°** sobre el borde de la pantalla.
   - **Pata trasera** de placa + diagonal (solo la hipotenusa del triángulo, sin tocar la pantalla), fija con clips: siempre perpendicular a la pantalla, sin hacer palanca.
   - **Pata hasta la mesa** con varilla M8, porque el peso le ganaba a la bisagra del notebook.
   - **Caja de MDF de 3 mm solo para la electrónica**, con uniones dentadas y **grabado tipo cerebro en todas las caras**. Lleva hoyos para los cables de los ojos, el USB del Arduino y un **módulo USB-C** de alimentación en una cápsula impresa.
5. **Todo es paramétrico en código (CadQuery):** las piezas salen de scripts en Python a partir de medidas reales. Los scripts revisan choques contra la pantalla y entre piezas, y que se puedan imprimir sin soportes.
6. **Ajustes de fabricación:**
   - el kerf del MDF pasó de 0,15 a 0 mm porque las uniones quedaban muy apretadas;
   - el grabado del frente y la parte de atrás estaba al revés y hubo que reflejarlo;
   - los agujeros se agrandaron para tornillos M3;
   - el soporte de la UNO estaba invertido;
   - los clips se rediseñaron para imprimirse de lado.

### 3.8 La entrega
- Página web con la estética Insta3D (negro, verde #1a7a2e, Barlow Condensed, patrón de puntos).
- Tiene **ojos interactivos** que siguen el mouse, hacen las 16 expresiones y se duermen si nadie se mueve.
- Además: panel en vivo, diagrama del sistema, flujo de interacción, fabricación, galerías de estudio y de proceso, y descargas.

## 4. Arquitectura

```
Cámara ─► seguir.py (YuNet · MediaPipe · SFace) ─► USB serie 115200 ─► Arduino UNO ─► I2C ─► PCA9685 ─► 6 × SG90
              ▲ │  UDP 47800/47801 (expresiones, quién habla, caras)
              │ ▼
Micrófono ─► hablar.py (Whisper MLX · Claude · voz · boca pygame) ◄──► API de Claude
                    │ UDP 47802 (forma de la boca)
                    ▼
            servidor.py (http://localhost:8730) ◄── página web + panel en vivo (SSE)
```

**Protocolo con el Arduino:**
- `M x y`: mirada, de −100 a 100.
- `E n`: expresión de 0 a 16 (15 = dormido, 16 = despertar).
- `D`: diagnóstico.

**Archivos de aviso entre los programas:** `durmiendo`, `saludar`, `decir` y `escaneando`.

## 5. Qué subir a GitHub

El `.gitignore` de la raíz ya está preparado. Con `git init` y `git add .` quedan **solo** los archivos que se pueden publicar.

| Subir | Qué es |
|---|---|
| `README.md` | Documentación del repositorio |
| `seguir.py`, `hablar.py`, `servidor.py`, `serie.py` | Programas |
| `*.command`, `descargar_modelos.sh` | Lanzadores (macOS) |
| `requisitos.txt`, `requisitos_cad.txt` | Dependencias |
| `OjosAnimados/`, `OjosCalibracion/` | Sketches del Arduino |
| `calibracion.md` | Calibración de los servos |
| `conocimiento_escuela.ejemplo.md` | Plantilla. El real **no** se sube |
| `cabeza/*.py`, `cabeza/stl_base/`, `cabeza/laser/` | CAD paramétrico, STL y cortes láser |
| `web/` | Página de entrega (HTML/CSS/JS + imágenes + descargas) |
| `PROCESO_ENTREGA.md` | Este documento (opcional) |

**Para GitHub Pages:**
- Pages solo publica desde la raíz o desde `/docs`. Lo más simple es copiar `web/` a `docs/` o publicar con GitHub Actions desde `web/`.
- En Pages la página funciona entera, menos el panel en vivo: sin `servidor.py` muestra el aviso "ábrela con pagina.command". Los ojos interactivos sí funcionan.

**Licencia, revisar antes de publicar:**
- El EyeMech es de Will Cogley y su repositorio no declara una licencia estándar (aparece como "Other"). Hay que leer sus condiciones antes de subir `cabeza/eyemech_base.stl`, que se sacó de su 3MF.
- Si hay dudas, se excluye ese STL (agregarlo al `.gitignore`) y se pone el enlace a su repositorio. Los scripts `cabeza/vista.py` y `cabeza/plano.py` lo necesitan para dibujar.
- Las piezas propias (ganchos, pata, cuna, soportes, cápsula, caja, base) son diseño nuestro.
- Sugerencia: código con licencia MIT y piezas con CC BY-NC-SA 4.0, con crédito al EyeMech.

## 6. Lo que nunca se publica

- `clave_anthropic.txt`: la clave de la API. **Es secreta: no abrirla, no copiarla, no pegarla en ningún lado.**
- `caras_conocidas.json`, `personas.json`: huellas de caras y ropa. Son datos biométricos.
- `memoria_robot.json`: lo que el robot recuerda de conversaciones.
- `conocimiento_escuela.md`: tiene datos de profesores reales, incluidos datos personales contados por el equipo.
- `registro_*.txt`, `hablante.jpg`, `caras.jpg`, `camara_actual.jpg`, `vista_web.jpg`, `estado_seguir.json`, `calibracion_habla.csv`: lo que capta la cámara y el micrófono, y registros con nombres.
- `fotos_proyecto/`: originales sin recortar. Salen personas. En la página van las versiones recortadas de `web/img/`.
- `.venv/`, `.venv-cad/`, `modelos/`: se instalan o descargan.

Antes de hacer push, revisar que la clave no aparezca en nada:

```bash
cd ~/RobotFace && git grep -n "sk-ant" -- . ':!README.md' ':!PROCESO_ENTREGA.md'
```

Debe salir vacío. El README y este archivo solo tienen el ejemplo `sk-ant-...`.

## 7. Texto para el portafolio

**Título:** RobotFace: Claude físico y expresivo

**Bajada:** Una interfaz sin pantalla de botones. Mirada, gesto y voz para conversar con una IA.

**Descripción corta (≈70 palabras):**
Unos ojos animatrónicos montados sobre la pantalla de un notebook que te miran, conversan contigo por voz con Claude y expresan emociones con los párpados. Diseñé la interacción completa: un ciclo de vida (duerme si no hay nadie, despierta al verte y te saluda), 16 expresiones sincronizadas con lo que dice, reconocimiento facial con consentimiento y la montura física en acrílico, MDF e impresión 3D, toda paramétrica.

**Descripción larga:**
- **Problema:** conversar con una IA es mirar una pantalla. ¿Qué pasa si la IA te mira de vuelta?
- **Interacción:**
  - estados en vez de menús: duerme, despierta, saluda, escucha, piensa y responde;
  - mira a quien habla;
  - se calla si la interrumpes;
  - solo "piensa en voz alta" cuando le haces una pregunta.
- **Expresión:** Claude elige una emoción por frase; los ojos la actúan y la boca en pantalla cambia de forma.
- **Ética:** la cara es un dato biométrico. Pregunta antes de recordarte, guarda todo en el computador y te olvida si se lo pides.
- **Objeto:** 4 iteraciones de montura hasta dejar el mecanismo a la vista sobre una base de acrílico. Ganchos fijos a 15°, pata a la mesa y una caja-cerebro grabada en láser para la electrónica.
- **Herramientas:**
  - Arduino, PCA9685, servos SG90;
  - Python, OpenCV, MediaPipe, Whisper (MLX), API de Claude, pygame;
  - CadQuery (CAD paramétrico), corte láser, impresión 3D (Bambu);
  - HTML/CSS/JS.

**Imágenes sugeridas (en `web/img/`):**

| Archivo | Uso |
|---|---|
| `estudio_tres_cuartos.jpg` | Portada: el objeto final |
| `estudio_lado.jpg` | Perfil: ganchos y pata |
| `estudio_arriba_arduino.jpg` | Mecanismo + electrónica |
| `estudio_frente_mdf.jpg` | Iteración descartada (frente de MDF) |
| `estudio_mecanismo.jpg` | El EyeMech y un párpado |
| `estudio_arriba.jpg` | Base de acrílico con los soportes |
| `proceso_caja_cerebro.jpg` | Caja con grabado de cerebro |
| `proceso_caja_abierta.jpg` | Electrónica dentro de la caja |
| `proceso_prueba_notebook.jpg` | Prueba de altura sobre el notebook |
| `boceto.jpg` | Boceto de la montura |
| `caja_mdf3.svg`, `base_acrilico5.svg` | Planos de corte láser |
| `bocas_emociones.png` | Bocas por emoción |
| `vista.png`, `pata_mesa.png`, `capsula_usbc.png` | Renders CAD |

**Para el portafolio falta grabar:**
- un video corto con el robot despertando y saludando;
- una conversación con expresiones;
- el escaneo de cara.

Una captura del panel en vivo también sirve (con permiso de quien salga en cámara).

## 8. Cómo correrlo (para el README o una demo)

1. Conectar la fuente de 5 V a los servos y el Arduino por USB al Mac.
2. Hacer doble clic en `pagina.command`: se abre Chrome en el panel.
3. Apretar **Encender robot**.

Sin el panel, también se pueden abrir `seguir.command` y `hablar.command`.

Instalación desde cero: ver `README.md` (uv + `requisitos.txt` + `descargar_modelos.sh` + tu propia clave de la API).

## 9. Todos los recursos en un paquete

Todo lo publicable está ordenado en **`~/Downloads/RobotFace_recursos/`**, y comprimido en `~/Downloads/RobotFace_recursos.zip` (25 MB). El índice está en `LEEME_INDICE.md`.

**Carpetas:**
- `01_codigo`
- `02_pagina_web`
- `03_fabricacion`: STL, SVG, renders y armado
- `04_fotos`: estudio en alta resolución, estudio para web y proceso recortado
- `05_documentos`
- `06_marca_insta3d`

Revisé que no tenga la clave ni datos de personas. Si cambia el código o la página, regenera con `web/armar.py` y vuelve a armar el paquete.
