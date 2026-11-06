# Sigue caras con la cámara del Mac y manda la mirada al Arduino.
# Mientras alguien habla (aviso de hablar.py), mira a la cara que mueve la boca, y la
# sigue mirando mientras el robot le responde. Si nadie habla y hay varias caras,
# cambia entre ellas cada cierto tiempo al azar.
# Uso: .venv/bin/python seguir.py [--ventana]
#   --ventana  muestra la imagen de la cámara con las caras y sus ojos marcados (la cruz roja
#              es donde mira el robot). En esa ventana: teclas 1-9 hacen una expresión,
#              w / s suben o bajan la mirada (se guarda en ajuste_mirada.txt), q para salir.
#              Botón "Escanear cara" (o tecla R), con permiso de la persona: se escribe el nombre,
#              Enter, y el robot la guía hablando por 6 ángulos (frente, lados, arriba, abajo) y
#              guarda una huella en cada uno. Esc o el botón cancelan.
#   --calibrar guarda las medidas de cada boca en calibracion_habla.csv
# Recibe de hablar.py por UDP (puerto 47800): "E n" expresión, "V 1/0" alguien habla,
# "R 1/0" el robot habla.
# Si no ve a nadie durante DORMIR_TRAS segundos se duerme: cierra los ojos y deja el archivo
# "durmiendo" para que hablar.py dibuje la boca roncando. Solo lo despierta ver una cara (el ruido no).
import glob, json, math, os, random, socket, sys, time
from pathlib import Path
from collections import deque
import cv2
import numpy as np
import serial
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision

# Puerto del Arduino: el primero que aparezca (cambia según en qué USB del Mac esté)
PUERTO = next(iter(sorted(glob.glob("/dev/cu.usbmodem*") + glob.glob("/dev/cu.usbserial*"))), None)
if PUERTO is None:
    sys.exit("No encuentro el Arduino: revisa el cable USB")
CAMARA = None  # None = buscar sola; o un número (0, 1, 2...) para fijar una

# Si los ojos miran al lado contrario, cambiar el signo
INVERTIR_X = False
INVERTIR_Y = False

# Cuánto giran los ojos según la posición de la cara en la imagen (1 = borde de la imagen = tope)
GANANCIA_X = 1.3
GANANCIA_Y = 0.7   # antes 1.5: miraba muy arriba

# Suavizado de la posición detectada (0..1, más alto = reacciona más rápido)
SUAVIZADO = 0.35

# Con varias caras y nadie hablando: segundos que mira a una antes de cambiar (mínimo, máximo)
CAMBIO_CARA = (1.5, 5.0)

# Puntaje mínimo de boca para considerar que una cara está hablando (ver --calibrar).
# El puntaje es cuánto más se mueve la boca que lo normal para esa misma cara.
UMBRAL_HABLA = 0.8
# Segundos de historia de cada boca que se usan para decidir quién habla
VENTANA = 1.0
# Caras a las que se les mide la boca en cada cuadro (las más grandes)
MAX_CARAS_BOCA = 4
# Las caras se buscan en una copia reducida de la imagen (mucho más rápido)
ANCHO_DETECCION = 960
# Detecciones más débiles o caras más chicas que esto se ignoran (suelen ser errores)
CONFIANZA_CARA = 0.75
CARA_MINIMA = 0.035      # fracción del ancho de la imagen
# Segundos que se recuerda una cara que dejó de verse (para que no cambie de número)
MEMORIA_CARA = 1.5
# Segundos que debe llevar vista una cara antes de poder ser elegida como hablante
EDAD_MINIMA = 0.5

# Se duerme si no ve a nadie durante este tiempo (segundos)
DORMIR_TRAS = 10.0
ARCHIVO_DORMIDO = Path(__file__).resolve().parent / "durmiendo"
ARCHIVO_SALUDAR = Path(__file__).resolve().parent / "saludar"   # para que hablar.py salude al despertar
ARCHIVO_DECIR = Path(__file__).resolve().parent / "decir"       # frase que hablar.py dice tal cual (escaneo)
ARCHIVO_ESCANEO = Path(__file__).resolve().parent / "escaneando"   # mientras escanea, hablar.py no conversa
ARCHIVO_ESTADO = Path(__file__).resolve().parent / "estado_seguir.json"   # para el panel de la página
ARCHIVO_VISTA_WEB = Path(__file__).resolve().parent / "vista_web.jpg"   # cámara con las caras, para la página
DORMIDO, DESPERTAR = 15, 16  # expresiones del Arduino: dormido y despertar mirando a la persona

# Foto de la cámara que usa hablar.py cuando Claude quiere mirar
FOTO_ACTUAL = "camara_actual.jpg"
CADA_CUANTO_FOTO = 0.3  # segundos
# Segundos que sigue mirando a quien habló después de que terminó: cubre lo que el robot
# se demora en pensar la respuesta (mientras habla, lo mira siempre)
MIRAR_DESPUES = 10.0
# Puntaje acumulado en la frase (puntaje × segundos) para decidir que una cara es quien habla
UMBRAL_ACUMULADO = 0.4

EXPRESIONES = ["sorpresa", "sueño", "enojo", "sospecha", "guiño",
               "curioso", "feliz", "rodar los ojos", "mirar alrededor"]

mostrar = "--ventana" in sys.argv
# --calibrar guarda en calibracion_habla.csv las medidas de cada boca en cada cuadro
calibrar = "--calibrar" in sys.argv

arduino = serial.Serial(PUERTO, 115200, timeout=0)
time.sleep(2.5)  # el Uno se reinicia al abrir el puerto

# Avisos que llegan desde hablar.py
PUERTO_EXPRESIONES = 47800
# Al terminar cada frase se le dice a hablar.py si alguien frente a la cámara movía la boca
PUERTO_RESPUESTA = 47801
respuestas_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
avisos_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
avisos_udp.bind(("127.0.0.1", PUERTO_EXPRESIONES))
avisos_udp.setblocking(False)


def abrir_camara():
    # Prueba las cámaras en orden y usa la primera que entregue imagen (no negra).
    # La 0 a veces es la del iPhone o una cámara virtual.
    for indice in ([CAMARA] if CAMARA is not None else [1, 0, 2, 3]):
        cam = cv2.VideoCapture(indice, cv2.CAP_AVFOUNDATION)
        if not cam.isOpened():
            continue
        for _ in range(30):  # la cámara del Mac entrega cuadros negros al encender
            ok, imagen = cam.read()
            if ok and imagen.mean() > 8:
                print(f"Usando cámara {indice}")
                return cam
            time.sleep(0.05)
        print(f"Cámara {indice}: imagen negra, pruebo la siguiente")
        cam.release()
    sys.exit("Ninguna cámara entregó imagen (¿permiso en Privacidad y seguridad → Cámara?)")


puntos_cara = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path="modelos/face_landmarker.task"),
    num_faces=1, running_mode=vision.RunningMode.IMAGE))

# Volumen del micrófono reciente (llega de hablar.py), para comparar con las bocas
volumen_mic = deque(maxlen=200)


def apertura_boca(imagen, fila):
    """Distancia entre los labios como % del alto de la cara, con MediaPipe sobre un
    recorte de la cara. None si no la pudo medir."""
    x, y, w, h = fila[:4]
    cx, cy, lado = x + w / 2, y + h / 2, max(w, h) * 1.8
    alto_img, ancho_img = imagen.shape[:2]
    x0, y0 = int(max(0, cx - lado / 2)), int(max(0, cy - lado / 2))
    x1, y1 = int(min(ancho_img, cx + lado / 2)), int(min(alto_img, cy + lado / 2))
    if x1 - x0 < 20 or y1 - y0 < 20:
        return None
    recorte = cv2.resize(cv2.cvtColor(imagen[y0:y1, x0:x1], cv2.COLOR_BGR2RGB), (256, 256))
    r = puntos_cara.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(recorte)))
    if not r.face_landmarks:
        return None
    p = r.face_landmarks[0]
    # 13 y 14: centro del labio superior e inferior (por dentro); 10 y 152: frente y mentón
    labios = np.hypot(p[13].x - p[14].x, p[13].y - p[14].y)
    cara = np.hypot(p[10].x - p[152].x, p[10].y - p[152].y)
    return float(labios / cara * 100) if cara > 0 else None


# ---------------- Ropa: para reconocer a las personas que el robot ya conoce ----------------
ARCHIVO_PERSONAS = "personas.json"   # nombre -> colores de la ropa (histograma)
PARECIDO_MINIMO = 0.55               # de 0 a 1: cuánto debe parecerse la ropa para reconocerla
FOTO_HABLANTE = "hablante.jpg"       # recorte de quien habló, para que Claude lo vea
FOTO_CARAS = "caras.jpg"             # todas las caras visibles numeradas, para "mira a ..."
# Reconocimiento facial (todo local): huella de 128 números de cada cara con el modelo SFace de
# OpenCV. Solo se guarda la cara de quien dio permiso (hablar.py lo pregunta), en caras_conocidas.json.
MODELO_CARAS = "modelos/sface.onnx"
ARCHIVO_CARAS = "caras_conocidas.json"   # nombre -> lista de huellas
PARECIDO_CARA = 0.40                     # similitud mínima (coseno) para decir que es esa persona
CADA_HUELLA = 0.6                        # segundos entre huellas de una misma cara (ahorra CPU)
MAX_HUELLAS = 8                          # huellas guardadas por persona (distintos ángulos y luces)
ANCHO_MIN_HUELLA = 70                    # caras más chicas (lejos) no sirven para reconocer


def zona_ropa(imagen, fila):
    """Recorte del torso bajo la cara (donde está la ropa), o None si no se ve."""
    x, y, w, h = fila[:4]
    alto_img, ancho_img = imagen.shape[:2]
    x0, x1 = int(max(0, x + w / 2 - 1.1 * w)), int(min(ancho_img, x + w / 2 + 1.1 * w))
    y0, y1 = int(min(alto_img, y + 1.25 * h)), int(min(alto_img, y + 2.6 * h))
    if x1 - x0 < 20 or y1 - y0 < 20:
        return None
    return imagen[y0:y1, x0:x1]


def colores_ropa(imagen, fila):
    """Histograma de color (tono y saturación) de la ropa, normalizado. None si no se ve."""
    zona = zona_ropa(imagen, fila)
    if zona is None:
        return None
    hsv = cv2.cvtColor(zona, cv2.COLOR_BGR2HSV)
    # Sin los píxeles muy oscuros, donde el tono no significa nada
    mascara = cv2.inRange(hsv, (0, 0, 35), (180, 255, 255))
    hist = cv2.calcHist([hsv], [0, 1], mascara, [16, 8], [0, 180, 0, 256]).flatten()
    # La parte oscura cuenta como un color más (ropa negra)
    oscuro = float((hsv[:, :, 2] < 35).mean())
    hist = np.append(hist / max(1.0, hist.sum()) * (1 - oscuro), oscuro)
    return hist / max(1e-9, hist.sum())


def parecido(a, b):
    """De 0 a 1: cuánto se parecen dos histogramas de ropa (intersección)."""
    return float(np.minimum(a, b).sum())


def cargar_personas():
    try:
        return {n: np.array(d["ropa"]) for n, d in json.loads(Path(ARCHIVO_PERSONAS).read_text()).items()}
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return {}


def guardar_personas(personas):
    Path(ARCHIVO_PERSONAS).write_text(json.dumps(
        {n: {"ropa": [round(float(v), 5) for v in h]} for n, h in personas.items()}, ensure_ascii=False, indent=1))


def cargar_caras():
    try:
        return {n: [np.array(h, dtype=np.float32) for h in hs] for n, hs in json.loads(Path(ARCHIVO_CARAS).read_text()).items()}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def guardar_caras(caras_):
    Path(ARCHIVO_CARAS).write_text(json.dumps({n: [h.round(5).tolist() for h in hs] for n, hs in caras_.items()}))


def parecido_cara(huella, nombre):
    hs = caras_conocidas.get(nombre) or []
    return max((float(np.dot(huella, h)) for h in hs), default=0.0)


# Reconocimiento conjunto: la cara y la ropa votan juntas. Cada pista se pasa a una nota de 0 a 1
# (0 = no se parece, 1 = seguro que es) y se combinan: la cara pesa más, la ropa ayuda cuando la
# cara se ve de lado o lejos, y una cara claramente distinta le gana a una ropa parecida.
CARA_NO, CARA_SI = 0.20, 0.55        # coseno SFace: bajo esto no se parece, sobre esto es la persona
ROPA_NO, ROPA_SI = 0.35, 0.80        # intersección de colores de la ropa
PESO_CARA = 0.7                      # con las dos pistas: 70 % cara, 30 % ropa
SOLO_ROPA = 0.85                     # sin cara para comparar, la ropa sola vale un poco menos
NOTA_MINIMA = 0.5                    # nota combinada para decir que es esa persona
MEMORIA_VOTOS = 1.0                  # segundos: la nota se suaviza en el tiempo (no salta de persona)


def _nota(valor, no, si):
    return float(min(1.0, max(0.0, (valor - no) / (si - no))))


def notas_persona(cara, personas):
    """{nombre: (nota combinada, fuente)} para cada persona conocida, con lo que se ve ahora."""
    notas = {}
    for nombre in set(caras_conocidas) | set(personas):
        n_cara = (_nota(parecido_cara(cara.huella, nombre), CARA_NO, CARA_SI)
                  if cara.huella is not None and nombre in caras_conocidas else None)
        n_ropa = (_nota(parecido(cara.ropa, personas[nombre]), ROPA_NO, ROPA_SI)
                  if cara.ropa is not None and nombre in personas else None)
        if n_cara is not None and n_ropa is not None:
            notas[nombre] = (PESO_CARA * n_cara + (1 - PESO_CARA) * n_ropa, "cara+ropa")
            if n_cara >= 0.95:                      # la cara sola ya es segura
                notas[nombre] = (max(notas[nombre][0], n_cara), "cara+ropa")
        elif n_cara is not None:
            notas[nombre] = (n_cara, "cara")
        elif n_ropa is not None:
            notas[nombre] = (n_ropa * SOLO_ROPA, "ropa")
    return notas


def reconocer(cara, personas):
    """Nombre de la persona conocida y su nota de 0 a 1 (o None, nota). Junta la cara y la ropa y
    suaviza en el tiempo por cada cara seguida. Deja en cara.fuente "cara+ropa", "cara" o "ropa"."""
    ahora_ = time.time()
    notas = notas_persona(cara, personas)
    votos = getattr(cara, "votos", None)
    if votos is None:
        votos = cara.votos = {}
    dt = ahora_ - getattr(cara, "t_votos", ahora_ - 10)
    cara.t_votos = ahora_
    a = 1.0 - math.exp(-max(0.0, dt) / MEMORIA_VOTOS)
    for nombre in set(votos) | set(notas):
        nueva = notas.get(nombre, (0.0, None))[0]
        votos[nombre] = votos.get(nombre, nueva) * (1 - a) + nueva * a
    cara.fuente = None
    if not votos:
        return None, 0.0
    nombre = max(votos, key=votos.get)
    if votos[nombre] >= NOTA_MINIMA:
        cara.fuente = notas.get(nombre, (0, "ropa"))[1] or "ropa"
        return nombre, votos[nombre]
    return None, votos[nombre]


def tomar_huella(cara, imagen):
    """Huella de la cara (128 números, largo 1), promediada con las anteriores de la misma cara."""
    try:
        alineada = reconocedor.alignCrop(imagen, cara.fila[:15].reshape(1, -1).astype(np.float32))
        h = reconocedor.feature(alineada).flatten().astype(np.float32)
    except cv2.error:
        return
    h /= np.linalg.norm(h) + 1e-9
    cara.huella = h if cara.huella is None else (cara.huella * 0.6 + h * 0.4)
    cara.huella /= np.linalg.norm(cara.huella) + 1e-9
    cara.t_huella = time.time()


def huella_nueva(cara, imagen):
    """Huella de la cara solo de esta imagen (sin promediar): para el escaneo, una por ángulo."""
    try:
        alineada = reconocedor.alignCrop(imagen, cara.fila[:15].reshape(1, -1).astype(np.float32))
        h = reconocedor.feature(alineada).flatten().astype(np.float32)
    except cv2.error:
        return None
    return h / (np.linalg.norm(h) + 1e-9)


# Escaneo guiado: (lo que dice el robot, texto en pantalla)
PASOS_ESCANEO = [
    ("Mira de frente a la cámara.", "Mira de frente"),
    ("Gira un poquito la cabeza hacia tu izquierda.", "Gira a tu izquierda"),
    ("Ahora hacia tu derecha.", "Gira a tu derecha"),
    ("Levanta un poco la barbilla.", "Barbilla arriba"),
    ("Baja un poco la barbilla.", "Barbilla abajo"),
    ("Y de nuevo de frente.", "De frente otra vez"),
]
ESPERA_PASO = 2.2        # segundos entre la instrucción y la captura (para que alcance a moverse)
PLAZO_PASO = 7.0         # si en este tiempo no ve bien la cara, salta el paso
BOTON = (0, 0, 0, 0)     # dónde quedó dibujado el botón (x0, y0, x1, y1), para el clic


def decir(texto):
    """Que hablar.py lo diga con su voz y su boca (si no está abierto, no pasa nada)."""
    try:
        ARCHIVO_DECIR.write_text(texto)
    except OSError:
        pass


def clic_ventana(evento, x, y, _flags, _param):
    global clic_boton
    if evento == cv2.EVENT_LBUTTONDOWN and BOTON[0] <= x <= BOTON[2] and BOTON[1] <= y <= BOTON[3]:
        clic_boton = True


def guardar_foto_caras(imagen, caras, personas):
    """Foto de la escena con cada cara numerada (de izquierda a derecha en la foto) y a quién
    se parece por la ropa. Devuelve {número: id de la cara}."""
    if imagen is None:
        return {}
    vista = imagen.copy()
    orden = sorted(caras, key=lambda c: c.centro[0])  # de izquierda a derecha en la foto
    numeros = {}
    for n, c in enumerate(orden, 1):
        x, y, w, h = (int(v) for v in c.fila[:4])
        nombre, _ = reconocer(c, personas)
        cv2.rectangle(vista, (x, y), (x + w, int(y + 2.6 * h)), (0, 160, 255), 3)
        etiqueta = f"{n}" + (f" ({nombre}?)" if nombre else "")
        cv2.putText(vista, etiqueta, (x, max(30, y - 12)), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 6)
        cv2.putText(vista, etiqueta, (x, max(30, y - 12)), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 220, 255), 2)
        numeros[n] = c.id
    escala = min(1.0, 1024 / vista.shape[1])
    vista = cv2.resize(vista, None, fx=escala, fy=escala) if escala < 1 else vista
    cv2.imwrite(FOTO_CARAS + ".tmp.jpg", vista, [cv2.IMWRITE_JPEG_QUALITY, 82])
    os.replace(FOTO_CARAS + ".tmp.jpg", FOTO_CARAS)
    return numeros


def guardar_foto_hablante(imagen, cara):
    """Guarda un recorte de la persona (cara y ropa) para que Claude vea quién le habló."""
    if imagen is None:
        return
    x, y, w, h = cara.fila[:4]
    alto_img, ancho_img = imagen.shape[:2]
    x0, x1 = int(max(0, x + w / 2 - 1.3 * w)), int(min(ancho_img, x + w / 2 + 1.3 * w))
    y0, y1 = int(max(0, y - 0.4 * h)), int(min(alto_img, y + 2.6 * h))
    if x1 - x0 < 20 or y1 - y0 < 20:
        return
    recorte = imagen[y0:y1, x0:x1]
    escala = min(1.0, 320 / max(recorte.shape[:2]))
    if escala < 1:
        recorte = cv2.resize(recorte, None, fx=escala, fy=escala)
    cv2.imwrite(FOTO_HABLANTE + ".tmp.jpg", recorte, [cv2.IMWRITE_JPEG_QUALITY, 85])
    os.replace(FOTO_HABLANTE + ".tmp.jpg", FOTO_HABLANTE)


class Cara:
    """Una cara seguida entre cuadros, con cuánto parece estar hablando."""
    siguiente_id = 1

    def __init__(self, fila):
        self.id = Cara.siguiente_id
        Cara.siguiente_id += 1
        self.aparecio = time.time()
        self.aperturas = deque(maxlen=120)  # (tiempo, apertura de la boca)
        self.movimiento = 0.0               # cuánto varía la boca en la ventana
        self.base = None                    # cuánto varía normalmente cuando nadie habla
        self.sincronia = 0.0                # parecido entre la boca y el sonido (-1..1)
        self.ropa = None                    # colores de la ropa (promedio de varios cuadros)
        self.huella = None                  # huella de la cara (reconocimiento facial)
        self.t_huella = 0.0
        self.fuente = None                  # "cara" o "ropa": cómo se la reconoció
        self.visible = True
        self.actualizar(fila, None)

    @property
    def edad(self):
        return time.time() - self.aparecio

    def actualizar(self, fila, imagen):
        x, y, w, h = fila[:4]
        self.fila = fila
        self.centro = (x + w / 2, y + h / 2)
        # Punto al que mira el robot: entre los ojos de la persona (marcas 4-7 de YuNet)
        self.ojos = ((fila[4] + fila[6]) / 2, (fila[5] + fila[7]) / 2)
        self.ancho = w
        self.visto = time.time()
        self.visible = True
        if imagen is None:
            return
        apertura = apertura_boca(imagen, fila)
        if apertura is not None:
            self.aperturas.append((self.visto, apertura))
        ropa = colores_ropa(imagen, fila)
        if ropa is not None:
            self.ropa = ropa if self.ropa is None else 0.9 * self.ropa + 0.1 * ropa
        self.calcular()

    def calcular(self):
        """Quien habla abre y cierra la boca seguido, al mismo ritmo que el sonido."""
        recientes = [(t, a) for t, a in self.aperturas if self.visto - t < VENTANA]
        if len(recientes) < 5:
            self.movimiento = self.sincronia = 0.0
            return
        tiempos = np.array([t for t, _ in recientes])
        bocas = np.array([a for _, a in recientes])
        self.movimiento = float(bocas.std())
        sonido = [(t, v) for t, v in volumen_mic if self.visto - t < VENTANA + 0.2]
        self.sincronia = 0.0
        if len(sonido) >= 5 and bocas.std() > 1e-3:
            niveles = np.interp(tiempos, [t for t, _ in sonido], [v for _, v in sonido])
            if niveles.std() > 1e-6:
                self.sincronia = float(np.corrcoef(bocas, niveles)[0, 1])

    def aprender_base(self):
        """Se llama cuando nadie habla: aprende el temblor normal de la medida de esta cara."""
        if self.movimiento > 0:
            self.base = self.movimiento if self.base is None else 0.97 * self.base + 0.03 * self.movimiento

    @property
    def puntaje(self):
        if self.edad < EDAD_MINIMA:
            return 0.0
        extra = self.movimiento - 1.3 * (self.base if self.base is not None else 0.3)
        return max(0.0, extra) * (1 + max(0.0, self.sincronia))


def emparejar(caras, filas, imagen):
    """Asocia cada cara detectada con una que ya se seguía (aunque se haya perdido hace
    poco) y les mide la boca a las más grandes."""
    ahora = time.time()
    caras = [c for c in caras if ahora - c.visto < MEMORIA_CARA]
    for c in caras:
        c.visible = False
    libres = list(caras)
    grandes = sorted(filas, key=lambda f: -f[2])[:MAX_CARAS_BOCA]
    for fila in sorted(filas, key=lambda f: -f[2]):
        medir = imagen if any(fila is g for g in grandes) else None
        centro = (fila[0] + fila[2] / 2, fila[1] + fila[3] / 2)
        cercana = min(libres, key=lambda c: (c.centro[0] - centro[0]) ** 2 + (c.centro[1] - centro[1]) ** 2,
                      default=None)
        if cercana and np.hypot(cercana.centro[0] - centro[0],
                                cercana.centro[1] - centro[1]) < max(fila[2], cercana.ancho) * 1.0:
            libres.remove(cercana)
            cercana.actualizar(fila, medir)
        else:
            nueva = Cara(fila)
            nueva.actualizar(fila, medir)
            caras.append(nueva)
    return caras


cam = abrir_camara()

detector = None
x_suave = y_suave = 0.0
ultimo_aviso = 0
seguidas = []         # todas las caras que se siguen, incluidas las perdidas hace poco
caras = []            # las que se ven en este cuadro
elegida = None        # id de la cara que está mirando
hablante = None       # id de la última cara que habló
proximo_cambio = 0.0
voz_activa = robot_habla = False
fin_voz = 0.0
ultima_foto = 0.0
acumulado = {}        # id de cara -> puntaje sumado durante la frase actual
personas = cargar_personas()
caras_conocidas = cargar_caras()
reconocedor = cv2.FaceRecognizerSF.create(MODELO_CARAS, "")
mirar_forzado = (None, 0.0)   # (id de cara, hasta cuándo) cuando le piden mirar a alguien
numeros_caras = {}            # número en la última foto de caras -> id de la cara
por_id_anterior = {}
ultima_imagen = None
ultimo_cuadro = time.time()
ultima_cara_vista = time.time()
registrando = None                 # nombre que se está escribiendo para registrar una cara (tecla R)
aviso_registro = ("", 0.0)
ultimo_estado = 0.0
ultima_vista_web = 0.0
escaneo = None                     # escaneo en curso: dict(nombre, paso, t_paso, huellas, ropa, flash)
clic_boton = False
ventana_lista = False
ARCHIVO_DECIR.unlink(missing_ok=True)
ARCHIVO_ESCANEO.unlink(missing_ok=True)
AJUSTE_ARCHIVO = Path(__file__).resolve().parent / "ajuste_mirada.txt"
try:
    ajuste_y = float(AJUSTE_ARCHIVO.read_text())
except Exception:
    ajuste_y = 0.0
dormido = False
ARCHIVO_DORMIDO.unlink(missing_ok=True)


def dormir():
    global dormido
    dormido = True
    arduino.write(f"E {DORMIDO}\n".encode())
    ARCHIVO_DORMIDO.touch()
    print("nadie a la vista hace rato: a dormir (zzz)")


def despertar(motivo):
    global dormido, ultima_cara_vista
    dormido = False
    ultima_cara_vista = time.time()
    ARCHIVO_DORMIDO.unlink(missing_ok=True)
    arduino.write(f"E {DESPERTAR}\n".encode())
    print(f"despierta: {motivo}")

if calibrar:
    registro = open("calibracion_habla.csv", "w")
    registro.write("tiempo,voz,cara,x,boca,base,sincronia,puntaje\n")
print("Siguiendo caras. Ctrl+C para salir.")
if mostrar:
    print("En la ventana de la cámara: " +
          ", ".join(f"{i + 1} {n}" for i, n in enumerate(EXPRESIONES)) + ", w/s subir o bajar la mirada, R registrar una cara, q salir")
try:
    while True:
        ok, imagen = cam.read()
        if not ok:
            time.sleep(0.05)
            continue
        alto, ancho = imagen.shape[:2]
        escala_det = min(1.0, ANCHO_DETECCION / ancho)
        if detector is None:
            detector = cv2.FaceDetectorYN.create(
                "modelos/yunet.onnx", "", (int(ancho * escala_det), int(alto * escala_det)), CONFIANZA_CARA)

        try:
            while True:
                orden = avisos_udp.recv(64).decode().strip()
                if orden.startswith("E "):
                    if not dormido:   # dormido no hace caso: solo lo despierta ver a alguien
                        arduino.write((orden + "\n").encode())
                    print(f"expresión desde la conversación: {orden}")
                elif orden in ("V 1", "V 0"):
                    if orden == "V 1" and not voz_activa:
                        acumulado = {}  # empieza una frase nueva
                    voz_activa = orden == "V 1"
                    if not voz_activa:
                        fin_voz = time.time()
                        # ¿Habló alguien que está frente a la cámara? (A <puntaje máximo> <caras>)
                        mejor = max(acumulado.values(), default=0.0)
                        quien = por_id_anterior.get(hablante)
                        nombre, valor = reconocer(quien, personas) if quien else (None, 0.0)
                        if quien is not None:
                            guardar_foto_hablante(ultima_imagen, quien)
                        etiqueta = f"{quien.fuente}:{nombre}" if nombre and quien is not None else "-"
                        respuestas_udp.sendto(f"A {mejor:.3f} {len(caras)} {valor:.2f} {etiqueta}".encode(),
                                              ("127.0.0.1", PUERTO_RESPUESTA))
                elif orden in ("R 1", "R 0"):
                    robot_habla = orden == "R 1"
                elif orden.startswith("P "):
                    # Recordar a una persona por su ropa: quien habló último (o la cara más grande)
                    nombre = orden[2:].strip()
                    quien = por_id_anterior.get(hablante) or max(caras, key=lambda c: c.ancho, default=None)
                    ok = quien is not None and quien.ropa is not None and nombre != ""
                    if ok:
                        personas[nombre] = quien.ropa.copy()
                        guardar_personas(personas)
                        print(f"recuerdo a {nombre} por su ropa (cara {quien.id})")
                    respuestas_udp.sendto(f"P {'1' if ok else '0'} {nombre}".encode(), ("127.0.0.1", PUERTO_RESPUESTA))
                elif orden.startswith("H "):
                    # Recordar la CARA de una persona (solo si dio permiso): quien habló último o la más grande
                    nombre = orden[2:].strip()
                    quien = por_id_anterior.get(hablante) or max(caras, key=lambda c: c.ancho, default=None)
                    ok = quien is not None and quien.huella is not None and nombre != ""
                    if ok:
                        caras_conocidas.setdefault(nombre, []).append(quien.huella.copy())
                        caras_conocidas[nombre] = caras_conocidas[nombre][-MAX_HUELLAS:]
                        guardar_caras(caras_conocidas)
                        print(f"recuerdo la cara de {nombre} (cara {quien.id})")
                    respuestas_udp.sendto(f"H {'1' if ok else '0'} {nombre}".encode(), ("127.0.0.1", PUERTO_RESPUESTA))
                elif orden.startswith("X "):
                    nombre = orden[2:].strip()
                    if personas.pop(nombre, None) is not None:
                        guardar_personas(personas)
                        print(f"olvidé la ropa de {nombre}")
                    if caras_conocidas.pop(nombre, None) is not None:
                        guardar_caras(caras_conocidas)
                        print(f"olvidé la cara de {nombre}")
                elif orden.startswith("L "):
                    # Mirar a una persona conocida: la cara visible con la ropa más parecida
                    nombre = orden[2:].strip()
                    candidata, valor = None, 0.0
                    for c in caras:     # la cara visible con mejor nota conjunta (cara + ropa)
                        nota = notas_persona(c, personas).get(nombre, (0.0, None))[0]
                        if nota > valor:
                            candidata, valor = c, nota
                    ok = candidata is not None and valor >= NOTA_MINIMA * 0.85
                    if ok:
                        mirar_forzado = (candidata.id, time.time() + 6.0)
                        print(f"miro a {nombre} (cara {candidata.id}, nota cara+ropa {valor:.2f})")
                    respuestas_udp.sendto(f"M {'1' if ok else '0'} {nombre}".encode(), ("127.0.0.1", PUERTO_RESPUESTA))
                elif orden == "F":
                    # Foto de todas las caras numeradas (para que Claude elija a quién mirar)
                    numeros_caras = guardar_foto_caras(ultima_imagen, list(por_id_anterior.values()), personas)
                    respuestas_udp.sendto(f"F {len(numeros_caras)}".encode(), ("127.0.0.1", PUERTO_RESPUESTA))
                elif orden.startswith("C "):
                    # Mirar a la cara número n de la última foto; si viene un nombre, se actualiza su ropa
                    partes = orden.split(" ", 2)
                    numero = int(partes[1]) if partes[1].isdigit() else 0
                    nombre = partes[2].strip() if len(partes) > 2 else ""
                    cara_id = numeros_caras.get(numero)
                    quien = por_id_anterior.get(cara_id)
                    ok = quien is not None
                    if ok:
                        mirar_forzado = (cara_id, time.time() + 6.0)
                        if nombre and quien.ropa is not None:
                            personas[nombre] = quien.ropa.copy()
                            guardar_personas(personas)
                        if nombre and nombre in caras_conocidas and quien.huella is not None:
                            caras_conocidas[nombre] = (caras_conocidas[nombre] + [quien.huella.copy()])[-MAX_HUELLAS:]
                            guardar_caras(caras_conocidas)
                        print(f"miro a la cara {numero}" + (f" ({nombre})" if nombre else ""))
                    respuestas_udp.sendto(f"C {'1' if ok else '0'} {numero}".encode(), ("127.0.0.1", PUERTO_RESPUESTA))
                elif orden.startswith("N "):
                    volumen_mic.append((time.time(), float(orden[2:])))
                elif orden.startswith("S ") and escaneo is None:
                    # Escanear una cara pedido desde la página (con el nombre ya escrito)
                    nombre = orden[2:].strip()[:40]
                    if nombre:
                        registrando = None
                        escaneo = dict(nombre=nombre, paso=0, t_paso=time.time() + 2.5, huellas=[], ropa=None, flash=0.0)
                        ARCHIVO_ESCANEO.write_text(nombre)
                        decir(f"Hola {nombre}, voy a escanear tu cara. {PASOS_ESCANEO[0][0]}")
                        print(f"escaneo pedido desde la página: {nombre}")
                elif orden == "S-" and escaneo is not None:
                    escaneo = None
                    ARCHIVO_ESCANEO.unlink(missing_ok=True)
                    aviso_registro = ("Escaneo cancelado", time.time() + 2)
                    decir("Ok, lo dejamos.")
        except BlockingIOError:
            pass

        if time.time() - ultima_foto > CADA_CUANTO_FOTO:
            # Se escribe en otro archivo y se reemplaza, para que nunca se lea a medias
            escala = min(1.0, 1024 / imagen.shape[1])  # más chica = Claude la ve más rápido
            foto = cv2.resize(imagen, None, fx=escala, fy=escala) if escala < 1 else imagen
            cv2.imwrite(FOTO_ACTUAL + ".tmp.jpg", foto, [cv2.IMWRITE_JPEG_QUALITY, 85])
            os.replace(FOTO_ACTUAL + ".tmp.jpg", FOTO_ACTUAL)
            ultima_foto = time.time()

        # Busca caras en la imagen reducida y lleva las coordenadas a la imagen completa
        reducida = cv2.resize(imagen, None, fx=escala_det, fy=escala_det) if escala_det < 1 else imagen
        _, filas = detector.detect(reducida)
        filas = [] if filas is None else [f.copy() for f in filas]
        for f in filas:
            f[:14] /= escala_det
        filas = [f for f in filas if f[2] > CARA_MINIMA * ancho]
        seguidas = emparejar(seguidas, filas, imagen)
        caras = [c for c in seguidas if c.visible]
        ahora = time.time()
        # Huellas de las caras (de a una por cuadro, la más atrasada, para no gastar tiempo)
        candidatas = [c for c in caras if c.ancho >= ANCHO_MIN_HUELLA and ahora - c.t_huella > CADA_HUELLA]
        if candidatas:
            tomar_huella(min(candidatas, key=lambda c: c.t_huella), imagen)
        dt_cuadro, ultimo_cuadro = min(0.2, ahora - ultimo_cuadro), ahora
        por_id = {c.id: c for c in caras}
        por_id_anterior, ultima_imagen = por_id, imagen
        # Estado para el panel de la página (cada medio segundo)
        if ahora - ultimo_estado > 0.5:
            ultimo_estado = ahora
            try:
                lista_caras = []
                for c in caras:
                    nombre_c, nota_c = reconocer(c, personas)
                    lista_caras.append({"id": c.id, "nombre": nombre_c, "fuente": c.fuente, "nota": round(float(nota_c), 2),
                                        "habla": round(float(c.puntaje), 2), "mirando": c.id == elegida})
                datos = {"t": ahora, "dormido": dormido, "caras": lista_caras, "conocidos": sorted(caras_conocidas),
                         "escaneo": None if escaneo is None else {"nombre": escaneo["nombre"], "paso": escaneo["paso"],
                                                                  "total": len(PASOS_ESCANEO), "capturas": len(escaneo["huellas"]),
                                                                  "instruccion": PASOS_ESCANEO[min(escaneo["paso"], len(PASOS_ESCANEO) - 1)][1]},
                         "aviso": aviso_registro[0] if aviso_registro[1] > ahora else ""}
                ARCHIVO_ESTADO.with_suffix(".tmp").write_text(json.dumps(datos, ensure_ascii=False))
                os.replace(ARCHIVO_ESTADO.with_suffix(".tmp"), ARCHIVO_ESTADO)
            except Exception as e:
                print(f"(no pude escribir el estado: {e})")
        # Dormir y despertar
        if any(c.edad >= EDAD_MINIMA for c in caras):
            if dormido:
                despertar("apareció alguien")
                nombre, _ = reconocer(max(caras, key=lambda c: c.ancho), personas)
                ARCHIVO_SALUDAR.write_text(nombre or "")
            ultima_cara_vista = ahora
        elif not dormido and ahora - ultima_cara_vista > DORMIR_TRAS:   # sin nadie a la vista, aunque haya ruido
            dormir()
        if not voz_activa and not robot_habla and ahora - fin_voz > 1.0:
            for c in caras:
                c.aprender_base()
        if calibrar:
            for c in caras:
                registro.write(f"{ahora:.3f},{int(voz_activa)},{c.id},{c.centro[0] / ancho:.3f},"
                               f"{c.movimiento:.3f},{c.base or 0:.3f},{c.sincronia:.3f},{c.puntaje:.3f}\n")

        if caras:
            if voz_activa:
                # Alguien habla: se suma el puntaje de cada cara durante toda la frase
                # y se mira a la que más acumula (un cuadro suelto no decide).
                for c in caras:
                    acumulado[c.id] = acumulado.get(c.id, 0.0) + c.puntaje * dt_cuadro
                visibles = sorted((acumulado.get(c.id, 0.0), c.id) for c in caras)
                lider_puntos, lider = visibles[-1]
                segundo = visibles[-2][0] if len(visibles) > 1 else 0.0
                if lider_puntos > UMBRAL_ACUMULADO and lider_puntos > 1.5 * segundo and hablante != lider:
                    quien = por_id[lider]
                    print(f"habla la cara {lider} (acumulado {lider_puntos:.2f} vs {segundo:.2f}; "
                          f"boca {quien.movimiento:.2f} vs normal {quien.base or 0:.2f})")
                    hablante = lider
                if hablante in por_id:
                    elegida = hablante
                elif len(caras) == 1:
                    elegida = hablante = caras[0].id
            elif mirar_forzado[0] in por_id and ahora < mirar_forzado[1]:
                # Le pidieron mirar a alguien
                elegida = mirar_forzado[0]
            elif (robot_habla or ahora - fin_voz < MIRAR_DESPUES) and hablante in por_id:
                # Le responde a quien habló
                elegida = hablante
            elif elegida not in por_id or (len(caras) > 1 and ahora >= proximo_cambio):
                # Nadie habla: mira a alguien al azar, empezando por la cara más grande
                otras = [c for c in caras if c.id != elegida]
                if elegida not in por_id:
                    elegida = max(caras, key=lambda c: c.ancho).id
                elif otras:
                    elegida = random.choice(otras).id
                proximo_cambio = ahora + random.uniform(*CAMBIO_CARA)
            if elegida not in por_id:  # la cara que miraba salió de la imagen
                elegida = max(caras, key=lambda c: c.ancho).id

            cara = por_id[elegida]
            cx = cara.ojos[0] / ancho * 2 - 1     # mira a los ojos: -1 izquierda de la imagen, +1 derecha
            cy = cara.ojos[1] / alto * 2 - 1      # -1 arriba de la imagen, +1 abajo

            # La imagen de la cámara no está en espejo: lo que aparece a la derecha
            # de la imagen está a la derecha del mecanismo (x negativo = su derecha).
            mx = -cx * GANANCIA_X
            my = -cy * GANANCIA_Y + ajuste_y
            if INVERTIR_X: mx = -mx
            if INVERTIR_Y: my = -my

            x_suave += (mx - x_suave) * SUAVIZADO
            y_suave += (my - y_suave) * SUAVIZADO
            ox = int(max(-100, min(100, x_suave * 100)))
            oy = int(max(-100, min(100, y_suave * 100)))
            arduino.write(f"M {ox} {oy}\n".encode())

            if ahora - ultimo_aviso > 1:
                bocas = "  ".join(f"cara {c.id}: puntaje {c.puntaje:.2f} (boca {c.movimiento:.2f}/{c.base or 0:.2f})"
                                  for c in caras)
                print(f"mirando cara {elegida}{' (habla)' if voz_activa else ''} | {bocas}")
                ultimo_aviso = ahora
        elif dormido:
            if ahora - ultimo_aviso > 10:
                arduino.write(f"E {DORMIDO}\n".encode())   # por si el Arduino se reinició
                ultimo_aviso = ahora
        elif ahora - ultimo_aviso > 2:
            print("sin cara (los ojos vuelven a mirar solos)")
            ultimo_aviso = ahora

        if mostrar:
            # Verde quien habla, naranjo a quien mira, gris las demás
            for c in caras:
                x, y, w, h = (int(v) for v in c.fila[:4])
                color = ((80, 220, 80) if c.id == hablante and (voz_activa or robot_habla)
                         else (0, 160, 255) if c.id == elegida else (150, 150, 150))
                cv2.rectangle(imagen, (x, y), (x + w, y + h), color, 2)
                for ex, ey in ((c.fila[4], c.fila[5]), (c.fila[6], c.fila[7])):   # los ojos de la persona
                    cv2.circle(imagen, (int(ex), int(ey)), 5, color, 2)
                if c.id == elegida:
                    ox_, oy_ = int(c.ojos[0]), int(c.ojos[1])
                    cv2.drawMarker(imagen, (ox_, oy_), (0, 0, 255), cv2.MARKER_CROSS, 22, 2)
            vista = cv2.flip(imagen, 1)
            for c in caras:
                x, y, w = int(ancho - c.fila[0] - c.fila[2]), int(c.fila[1]), int(c.fila[2])
                nombre, nota = reconocer(c, personas)
                quien_txt = f"{nombre} ({c.fuente} {nota:.2f})" if nombre else f"{c.id}"
                cv2.putText(vista, f"{quien_txt}: habla {c.puntaje:.1f}", (x, max(15, y - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            # ---------- Escaneo de caras: botón (o R) -> nombre -> 6 ángulos guiados por voz ----------
            ahora_v = time.time()
            if escaneo is not None:
                quien = por_id.get(elegida) or max(caras, key=lambda c: c.ancho, default=None)
                paso = escaneo["paso"]
                dicho, corto = PASOS_ESCANEO[paso]
                listo = ahora_v - escaneo["t_paso"] >= ESPERA_PASO
                if quien is not None:
                    # Marco de escaneo sobre la cara (en la vista en espejo): esquinas y línea que barre
                    x0 = int(ancho - quien.fila[0] - quien.fila[2]); y0 = int(quien.fila[1])
                    w_, h_ = int(quien.fila[2]), int(quien.fila[3])
                    m = int(w_ * 0.15); x0 -= m; y0 -= m; x1, y1 = x0 + w_ + 2 * m, y0 + h_ + 2 * m
                    bien = quien.ancho >= ANCHO_MIN_HUELLA
                    col = (90, 255, 170) if bien else (0, 140, 255)
                    L = max(14, (x1 - x0) // 5)
                    for (cx_, cy_, dx_, dy_) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
                        cv2.line(vista, (cx_, cy_), (cx_ + dx_ * L, cy_), col, 3)
                        cv2.line(vista, (cx_, cy_), (cx_, cy_ + dy_ * L), col, 3)
                    fase = (ahora_v * 0.9) % 2
                    yl = int(y0 + (y1 - y0) * (fase if fase < 1 else 2 - fase))
                    capa = vista.copy()
                    cv2.rectangle(capa, (x0, max(0, yl - 6)), (x1, yl + 6), col, -1)
                    cv2.addWeighted(capa, 0.35, vista, 0.65, 0, vista)
                    cv2.line(vista, (x0, yl), (x1, yl), col, 2)
                    if not bien:
                        cv2.putText(vista, "acercate", (x0, y1 + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, col, 2)
                    if listo and bien:
                        h_n = huella_nueva(quien, imagen)
                        if h_n is not None:
                            escaneo["huellas"].append(h_n)
                            if quien.ropa is not None:
                                escaneo["ropa"] = quien.ropa.copy()
                            escaneo["flash"] = ahora_v
                            print(f"escaneo: ángulo {paso + 1} de {len(PASOS_ESCANEO)} ({corto})")
                            listo = "hecho"
                if listo == "hecho" or ahora_v - escaneo["t_paso"] > PLAZO_PASO:
                    if listo != "hecho":
                        print(f"escaneo: no vi bien la cara en el paso {paso + 1}, sigo")
                    escaneo["paso"] += 1
                    escaneo["t_paso"] = ahora_v
                    if escaneo["paso"] < len(PASOS_ESCANEO):
                        decir(PASOS_ESCANEO[escaneo["paso"]][0])
                    else:   # terminó
                        nombre, hs = escaneo["nombre"], escaneo["huellas"]
                        if len(hs) >= 3:
                            caras_conocidas[nombre] = [h.copy() for h in hs][-MAX_HUELLAS:]
                            guardar_caras(caras_conocidas)
                            if escaneo["ropa"] is not None:
                                personas[nombre] = escaneo["ropa"]
                                guardar_personas(personas)
                            aviso_registro = (f"Listo: cara de {nombre} guardada ({len(hs)} angulos)", ahora_v + 4)
                            decir(f"Listo, {nombre}. Ya te tengo escaneado.")
                            print(f"escaneo: guardé la cara de {nombre} ({len(hs)} huellas)")
                        else:
                            aviso_registro = ("No alcance a verte bien: acercate y prueba otra vez", ahora_v + 4)
                            decir("No alcancé a verte bien. Acércate un poco y probemos otra vez.")
                        escaneo = None
                        ARCHIVO_ESCANEO.unlink(missing_ok=True)
                if escaneo is not None:
                    # Barra de arriba: instrucción y progreso
                    paso = escaneo["paso"]
                    cv2.rectangle(vista, (0, 0), (vista.shape[1], 80), (0, 0, 0), -1)
                    cv2.putText(vista, f"Escaneando a {escaneo['nombre']}  -  {PASOS_ESCANEO[paso][1]}",
                                (12, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 220, 255), 2)
                    total = len(PASOS_ESCANEO)
                    for i in range(total):
                        xi = 12 + i * 46
                        llena = i < paso
                        cv2.rectangle(vista, (xi, 54), (xi + 38, 68), (90, 255, 170) if llena else (90, 90, 90),
                                      -1 if llena else 2)
                    if ahora_v - escaneo["flash"] < 0.25:      # destello al capturar
                        blanco = np.full_like(vista, 255)
                        cv2.addWeighted(blanco, 0.45, vista, 0.55, 0, vista)
            elif registrando is not None:
                cv2.rectangle(vista, (0, 0), (vista.shape[1], 70), (0, 0, 0), -1)
                cv2.putText(vista, f"Nombre (Enter empieza el escaneo, Esc cancela): {registrando}_", (12, 45),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 220, 255), 2)
            elif aviso_registro[1] > ahora_v:
                cv2.rectangle(vista, (0, 0), (vista.shape[1], 70), (0, 0, 0), -1)
                cv2.putText(vista, aviso_registro[0], (12, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (90, 255, 170), 2)
            # Botón abajo a la derecha
            texto_b = "Cancelar escaneo" if (escaneo is not None or registrando is not None) else "Escanear cara"
            (tw, th), _ = cv2.getTextSize(texto_b, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
            bx1, by1 = vista.shape[1] - 16, vista.shape[0] - 16
            bx0, by0 = bx1 - tw - 36, by1 - th - 28
            BOTON = (bx0, by0, bx1, by1)
            cv2.rectangle(vista, (bx0, by0), (bx1, by1), (40, 40, 40) if texto_b != "Escanear cara" else (180, 110, 0), -1)
            cv2.rectangle(vista, (bx0, by0), (bx1, by1), (255, 255, 255), 2)
            cv2.putText(vista, texto_b, (bx0 + 18, by1 - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            if ahora_v - ultima_vista_web > 0.15:   # la misma vista, chica, para el panel de la página
                ultima_vista_web = ahora_v
                chica = cv2.resize(vista, (640, int(vista.shape[0] * 640 / vista.shape[1])))
                ok_jpg, jpg = cv2.imencode(".jpg", chica, [cv2.IMWRITE_JPEG_QUALITY, 70])
                if ok_jpg:
                    ARCHIVO_VISTA_WEB.with_suffix(".tmp").write_bytes(jpg.tobytes())
                    os.replace(ARCHIVO_VISTA_WEB.with_suffix(".tmp"), ARCHIVO_VISTA_WEB)
            cv2.imshow("Ojos - camara", vista)
            if not ventana_lista:
                cv2.setMouseCallback("Ojos - camara", clic_ventana)
                ventana_lista = True
            tecla = cv2.waitKey(1) & 0xFF
            empezar = False
            if clic_boton:
                clic_boton = False
                if escaneo is not None or registrando is not None:
                    tecla = 27                                # cancelar
                else:
                    empezar = True
            if escaneo is not None:
                if tecla == 27:
                    escaneo = None
                    ARCHIVO_ESCANEO.unlink(missing_ok=True)
                    aviso_registro = ("Escaneo cancelado", time.time() + 2)
                    decir("Ok, lo dejamos.")
                tecla = 255
            elif registrando is not None:
                if tecla == 27:                              # Esc
                    registrando = None
                elif tecla in (13, 10):                      # Enter: empieza el escaneo
                    nombre = registrando.strip()
                    registrando = None
                    if nombre:
                        escaneo = dict(nombre=nombre, paso=0, t_paso=time.time(), huellas=[], ropa=None, flash=0.0)
                        ARCHIVO_ESCANEO.write_text(nombre)
                        decir(f"Hola {nombre}, voy a escanear tu cara. {PASOS_ESCANEO[0][0]}")
                        escaneo["t_paso"] = time.time() + 2.5   # da tiempo al saludo antes del primer paso
                elif tecla in (8, 127):                      # borrar
                    registrando = registrando[:-1]
                elif 32 <= tecla < 127:
                    registrando += chr(tecla)
                tecla = 255
            elif tecla in (ord("r"), ord("R")) or empezar:
                registrando = ""
                decir("¿Cómo te llamas? Escríbelo en la pantalla.")
            if tecla == ord("q"):
                break
            if tecla in (ord("w"), ord("s")):   # ajuste fino de la altura de la mirada
                ajuste_y += 0.05 if tecla == ord("w") else -0.05
                AJUSTE_ARCHIVO.write_text(f"{ajuste_y:.2f}")
                print(f"ajuste de altura de la mirada: {ajuste_y:+.2f} (w sube, s baja)")
            if ord("1") <= tecla <= ord("9"):
                n = tecla - ord("0")
                arduino.write(f"E {n}\n".encode())
                print(f"expresión: {EXPRESIONES[n - 1]}")
except KeyboardInterrupt:
    pass
finally:
    ARCHIVO_DORMIDO.unlink(missing_ok=True)
    ARCHIVO_ESCANEO.unlink(missing_ok=True)
    ARCHIVO_ESTADO.unlink(missing_ok=True)
    ARCHIVO_VISTA_WEB.unlink(missing_ok=True)
    try:
        arduino.write(b"E 0\n")   # que no quede dormido: vuelve a animarse solo
    except Exception:
        pass
    cam.release()
    arduino.close()
    if mostrar:
        cv2.destroyAllWindows()
