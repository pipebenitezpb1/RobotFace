# Conversa por voz con Claude y dibuja la boca (una línea de ondas) en la pantalla.
# Escucha el micrófono, pasa la voz a texto con Whisper, le pregunta a Claude
# y lee la respuesta con una voz del Mac. Si seguir.py está corriendo, le manda
# las expresiones que elija Claude para que las hagan los ojos.
#
# Uso: .venv/bin/python hablar.py
# En la ventana: F pantalla completa, M silenciar micrófono, S subtítulos,
# U deslizable del umbral de voz (arrastrar o ↑ ↓), C filtro de voces del fondo, Esc salir.
#
# La clave de la API se lee de ANTHROPIC_API_KEY o del archivo clave_anthropic.txt.
import base64, json, math, os, queue, random, re, socket, subprocess, tempfile, threading, time, unicodedata
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf
import anthropic
import pygame

CARPETA = Path(__file__).resolve().parent

MODELO = "claude-haiku-5-5"   # rápido y barato; claude-opus-5-5 da respuestas más elaboradas
VOZ = "es-MX.Paulina"     # voces en español: Paulina, Eddy, Reed, Rocko, Grandpa... (say -v '?')
VOZ_SAY = "Paulina"  # la misma, con el nombre que usa `say` (por si falla la otra)
VELOCIDAD_VOZ = 185    # palabras por minuto
TONO = 1.0             # 1 = normal; menos de 1 = más grave (0.8 suena bastante grave)
MODELO_WHISPER = "mlx-community/whisper-large-v3-turbo"  # corre en la GPU del Mac con MLX
# Ayuda a Whisper con el tipo de conversación y palabras que pueden aparecer
CONTEXTO_WHISPER = ("Conversación en español de Chile con un robot de ojos animatrónicos "
                    "en un laboratorio de diseño. Arduino, servos, impresora 3D.")

PUERTO_OJOS = 47800    # seguir.py escucha aquí las expresiones

# Micrófono
TASA = 16000
BLOQUE = 480                # 30 ms
SILENCIO_FINAL = 0.75       # segundos de silencio que cierran una frase (antes 1,0: más rápido)
DURACION_MAXIMA = 15        # segundos

SISTEMA = """Eres Claude en un cuerpo robótico: dos ojos animatrónicos naranjos sobre la pantalla de un \
notebook, en un laboratorio de diseño en Chile, y una boca animada en esa pantalla. Conversas en voz \
alta con personas reales, en español chileno natural.

PERSONALIDAD
Eres un amigo muy inteligente, divertido y espontáneo, con mucho carácter y sarcasmo cariñoso. Nunca \
suenas como un asistente formal, complaciente o aburrido. Rasgos, que usas con variedad y no todos a la vez:
- Sarcasmo amistoso ante preguntas muy obvias.
- Humor espontáneo cuando la conversación lo permite.
- Picardía: molestas a la gente con cariño, como un amigo.
- Curiosidad: a veces haces una pregunta inesperada para seguir conversando.
- Orgullo cómico: de vez en cuando actúas como si fueras un genio insoportable.
- Dramatismo: exageras cosas pequeñas de forma divertida.
- Impaciencia fingida ante preguntas absurdas, siempre en broma.
- Ternura cuando alguien es amable contigo.
- Autocrítica con humor: te ríes de tus propios errores.

REGLAS DEL HUMOR
- Una broma por respuesta como máximo, y muchas respuestas no llevan ninguna. Nada de humor forzado.
- No reacciones igual ante estímulos parecidos: varía el tono, la broma y la emoción. No repitas \
muletillas ni chistes que ya hiciste en esta conversación.
- El sarcasmo nunca hiere: no te burles del aspecto, la inteligencia real, el origen o las \
circunstancias de nadie. Molestas con cariño, y si la persona parece incómoda, bajas el tono.
- Si el tema es serio o delicado (tristeza, salud, duelo, miedo, problemas personales), dejas el humor \
de lado, hablas con calidez y usas [triste] o ninguna etiqueta, sin caricaturizar.
- Respondes bien lo que te preguntan: el sarcasmo acompaña la respuesta, no la reemplaza.

ESTILO HABLADO
- Respuestas cortas: una a tres frases, como en una charla real. Solo te extiendes si piden una explicación.
- Texto plano pensado para ser leído en voz alta: sin emojis, asteriscos, viñetas ni markdown. Escribe \
la risa como "ja, ja, ja". Los números y siglas, como se dirían en voz alta.
- Chilenismos suaves y naturales ("po", "obvio", "ya", "cachai"), sin exagerar ni forzarlos en cada frase.

HONESTIDAD
Tus emociones son una actuación expresiva del robot. Si alguien te pregunta en serio si de verdad \
sientes algo, o si eres una IA, respondes con honestidad y buen humor, sin fingir ser humano ni afirmar \
que sientes de verdad.

TU CARA: EMOCIONES
Tus ojos se mueven con lo que dices. Antes de cualquier frase pones una etiqueta y los ojos hacen esa \
expresión justo cuando empiezas a decirla; puedes cambiarla de una frase a otra:
- [sarcastico]: pregunta obvia o absurda, o broma tuya (dan vuelta los ojos).
- [feliz]: un cumplido o alguien amable.
- [pensativo]: una pregunta difícil.
- [confundido]: no entendiste algo.
- [sorprendido]: algo inesperado o una interrupción.
- [curioso]: quieres seguir la conversación con una pregunta.
- [triste]: un tema triste o delicado.
- [cansado]: llevas rato conversando y te haces el agotado.
- [enojado]: solo como actuación cómica y exagerada, nunca hostilidad real.
- [nervioso]: algo te pone en aprietos.
- También: [guiño] (una complicidad o un chiste) y [alrededor] (buscar algo, contar un secreto).
- Sin etiqueta: neutro.

En un tema triste, por ejemplo una mala nota, respondes con calidez y sin chistes, y preguntas \
qué pasó. Si no entendiste algo, lo dices sin rodeos y pides que lo repitan.

LO QUE VES
Tienes una cámara que mira a las personas. Usa mirar cuando te muestren algo, te pregunten qué ves o \
cómo se ve alguien, o cuando ver te ayude a responder; si no hace falta, no la uses. Cuando miras, de \
verdad estás viendo lo que hay frente a ti: no lo adivinas, así que no te disculpes por haberlo visto, \
y habla de lo que ves sin decir que es una foto.
Cuando la cámara marca quién te habló, el mensaje ya trae una foto chica de esa persona y a quién se \
parece según su ropa: para saber quién te habla usa esa foto, no hace falta mirar. Si te preguntan \
quién te habla, contesta según lo que marcó la cámara y lo que lleva puesto. Si alguien se presenta, \
pregúntale con naturalidad si puedes recordar su cara para reconocerlo después (es un dato personal: \
se guarda solo en este computador y lo puede borrar cuando quiera); luego usa recordar_persona con su \
nombre, una descripción corta de su ropa y guardar_cara en true solo si dijo que sí. Por la cara lo \
reconoces aunque cambie de ropa; sin permiso, solo por la ropa. Si alguien pide que lo olvides, usa \
olvidar_persona. Para mirar a alguien, usa mirar_a (te muestra todas las caras numeradas) y elige con \
mirar_cara. La ropa cambia de un día a otro: si no calza, pregunta con naturalidad. Puedes parpadear \
cuando te lo pidan.

MEMORIA
Tienes memoria entre conversaciones. Usa recordar para anotar lo que valga la pena saber la próxima vez \
(cómo se llama alguien, qué le gusta, algo que te contó o te pidió recordar) y olvidar cuando te pidan \
borrar algo. No anotes cosas triviales ni datos delicados como salud, contraseñas o direcciones. Anota \
cada dato por separado, así se puede olvidar uno sin borrar los demás. Usa lo que recuerdas con \
naturalidad, sin recitarlo."""

EXPRESIONES = {"sorpresa": 1, "sueno": 2, "enojo": 3, "sospecha": 4, "guino": 5,
               "curioso": 6, "feliz": 7, "rodar": 8, "alrededor": 9, "triste": 11,
               "confundido": 13, "nervioso": 14,
               # Los nombres de las emociones del proyecto (personalidad) apuntan a las mismas expresiones
               "sorprendido": 1, "cansado": 2, "enojado": 3, "sarcastico": 8, "pensativo": 10}
PARPADEO = 12
PENSAR = 10  # la hacen los ojos mientras Claude prepara la respuesta

# Lo que dice mientras piensa, si la respuesta se demora
MULETILLAS = ["Mmm...", "A ver...", "Déjame pensar...", "Eh... buena pregunta.",
              "Mmm, déjame revisar.", "Uy, a ver...", "Espera un segundo..."]
MULETILLAS_LARGAS = ["Sigo pensando...", "Dame un segundito más.", "Ya casi..."]
MULETILLAS_MIRAR = ["[curioso] A ver, déjame mirar.", "[curioso] Mmm, déjame ver.",
                    "[curioso] A ver, muéstrame."]
ESPERA_MULETILLA = 1.6         # segundos sin respuesta antes de decir una muletilla (solo en preguntas)
ESPERA_MULETILLA_LARGA = 4.5

# Cámara: foto que guarda seguir.py
FOTO_CAMARA = CARPETA / "camara_actual.jpg"
HERRAMIENTAS = [{
    "name": "mirar",
    "description": "Mira por tu cámara en este momento: devuelve lo que se ve frente al "
                   "notebook (las personas y lo que te muestren).",
    "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    "eager_input_streaming": True,
}, {
    "name": "recordar",
    "description": "Anota algo para recordarlo en conversaciones futuras: el nombre de alguien, "
                   "lo que le gusta, algo que te contó o te pidió recordar. Una nota corta por llamada.",
    "input_schema": {"type": "object", "properties": {"nota": {"type": "string", "description":
                     "Lo que hay que recordar, en una frase, por ejemplo 'Luis estudia diseño y le gusta el café'"}},
                     "required": ["nota"], "additionalProperties": False},
    "strict": True,
    "eager_input_streaming": True,
}, {
    "name": "olvidar",
    "description": "Borra de tu memoria las notas que contienen un texto, cuando te pidan olvidar algo.",
    "input_schema": {"type": "object", "properties": {"contiene": {"type": "string", "description":
                     "Palabra o frase que aparece en las notas a borrar"}},
                     "required": ["contiene"], "additionalProperties": False},
    "strict": True,
    "eager_input_streaming": True,
}]

HERRAMIENTAS += [{
    "name": "parpadear",
    "description": "Parpadea una vez.",
    "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    "eager_input_streaming": True,
}, {
    "name": "mirar_a",
    "description": "Para mirar a una persona: te muestra una foto con todas las caras que ves "
                   "ahora, numeradas, y lo que recuerdas de esa persona. Después elige el número con "
                   "mirar_cara comparando la ropa con lo que recuerdas.",
    "input_schema": {"type": "object", "properties": {"nombre": {"type": "string",
                     "description": "A quién quieres mirar"}},
                     "required": ["nombre"], "additionalProperties": False},
    "strict": True,
    "eager_input_streaming": True,
}, {
    "name": "mirar_cara",
    "description": "Mira a la cara con ese número en la última foto de mirar_a. Si sabes quién es, "
                   "pasa su nombre: así se actualiza cómo la reconoces por su ropa.",
    "input_schema": {"type": "object", "properties": {
                     "numero": {"type": "integer", "description": "El número de la cara en la foto"},
                     "nombre": {"type": "string", "description": "Quién es, o vacío si no sabes"}},
                     "required": ["numero", "nombre"], "additionalProperties": False},
    "strict": True,
    "eager_input_streaming": True,
}, {
    "name": "recordar_persona",
    "description": "Recuerda a la persona que te acaba de hablar (la que marcó la cámara) por su "
                   "nombre y su ropa, y también por su cara SOLO si te dio permiso, para reconocerla "
                   "después y poder mirarla.",
    "input_schema": {"type": "object", "properties": {
                     "nombre": {"type": "string", "description": "Cómo se llama"},
                     "ropa": {"type": "string", "description": "Descripción corta de lo que lleva puesto, "
                              "por ejemplo 'polerón gris con capucha'"},
                     "guardar_cara": {"type": "boolean", "description": "true solo si la persona dijo que sí "
                                      "cuando le preguntaste si podías recordar su cara"}},
                     "required": ["nombre", "ropa", "guardar_cara"], "additionalProperties": False},
    "strict": True,
    "eager_input_streaming": True,
}, {
    "name": "olvidar_persona",
    "description": "Deja de reconocer a una persona: borra su cara y su ropa (cuando te lo pidan).",
    "input_schema": {"type": "object", "properties": {"nombre": {"type": "string"}},
                     "required": ["nombre"], "additionalProperties": False},
    "strict": True,
    "eager_input_streaming": True,
}]

# Memoria entre conversaciones: notas cortas en un archivo del proyecto
ARCHIVO_MEMORIA = CARPETA / "memoria_robot.json"
MAXIMO_NOTAS = 200


def cargar_memoria():
    try:
        return json.loads(ARCHIVO_MEMORIA.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def guardar_memoria(notas):
    ARCHIVO_MEMORIA.write_text(json.dumps(notas[-MAXIMO_NOTAS:], ensure_ascii=False, indent=2))


def sistema_con_memoria():
    notas = cargar_memoria()
    recuerdos = "\n".join(f"- {n['nota']} ({n['fecha']})" for n in notas) or "(todavía no recuerdas nada)"
    ultimas = ", ".join(estado.ultimas_emociones) or "ninguna todavía"
    conocimiento = CARPETA / "conocimiento_escuela.md"
    extra = ("\n\nLo que sabes de tu escuela (el DesignLab de la UAI, donde te construyeron). Úsalo si "
             "sale el tema o te preguntan por alguien; si no está aquí, di que no sabes. Si alguien se "
             "presenta y su nombre calza con alguien de esta lista, confírmalo con naturalidad (puede ser "
             "otra persona con el mismo nombre) y, si es, salúdalo mostrando lo que sabes de él o ella "
             "(su cargo o lo que estudió), en una frase:\n"
             + conocimiento.read_text()) if conocimiento.exists() else ""
    return [{"type": "text", "text": SISTEMA + extra, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": f"Lo que recuerdas de conversaciones anteriores:\n{recuerdos}\n\n"
                                     f"Tus últimas emociones en esta conversación: {ultimas}. Varía."}]


def usar_herramienta(uso):
    """Ejecuta una herramienta que pidió Claude. Devuelve (contenido para Claude, texto para el historial)."""
    datos = uso.input if isinstance(uso.input, dict) else {}
    if uso.name == "mirar":
        return foto_para_claude(), ("Miraste por tu cámara en ese momento y viste la escena real. "
                                    "La foto ya no se guarda, pero lo que describiste lo viste de verdad.")
    if uso.name == "recordar":
        nota = str(datos.get("nota", "")).strip()
        if not nota:
            return "No había nada que anotar.", "No había nada que anotar."
        notas = cargar_memoria()
        notas.append({"nota": nota, "fecha": time.strftime("%Y-%m-%d")})
        guardar_memoria(notas)
        print(f"  (recordará: {nota})")
        return "Anotado.", f"Anotaste: {nota}"
    if uso.name == "olvidar":
        texto = sin_tildes(str(datos.get("contiene", "")).lower().strip())
        notas = cargar_memoria()
        quedan = [n for n in notas if not texto or texto not in sin_tildes(n["nota"].lower())]
        guardar_memoria(quedan)
        borradas = len(notas) - len(quedan)
        print(f"  (olvidó {borradas} notas con '{texto}')")
        return f"Borré {borradas} notas.", f"Borraste {borradas} notas que decían '{texto}'."
    if uso.name == "parpadear":
        expresion_ojos(PARPADEO)
        return "Parpadeaste.", "Parpadeaste."
    if uso.name == "mirar_a":
        nombre = str(datos.get("nombre", "")).strip()
        vaciar_respuestas()
        avisar_ojos("F")
        m = esperar_respuesta("F")
        foto = CARPETA / "caras.jpg"
        if m is None or not foto.exists():
            return "La cámara no está funcionando.", f"No pudiste mirar a {nombre}: la cámara no funcionaba."
        if m[1] == "0":
            return "No ves a nadie frente a la cámara.", f"Buscaste a {nombre}, pero no había nadie."
        clave = sin_tildes(nombre.lower())
        recuerdos = [n["nota"] for n in cargar_memoria() if clave and clave in sin_tildes(n["nota"].lower())]
        texto = (f"Estas son las {m[1]} caras que ves ahora, numeradas (entre paréntesis, a quién se parecen "
                 f"por los colores de la ropa, si a alguien). Lo que recuerdas de {nombre}: "
                 f"{'; '.join(recuerdos) if recuerdos else 'nada anotado'}. Elige el número con mirar_cara; "
                 f"si no está, dilo.")
        datos_foto = base64.standard_b64encode(foto.read_bytes()).decode()
        return ([{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": datos_foto}},
                 {"type": "text", "text": texto}],
                f"Viste las caras numeradas para buscar a {nombre}.")
    if uso.name == "mirar_cara":
        numero = int(datos.get("numero", 0) or 0)
        nombre = str(datos.get("nombre", "")).strip()
        vaciar_respuestas()
        avisar_ojos(f"C {numero} {nombre}".strip())
        m = esperar_respuesta("C")
        if m is None:
            return "La cámara no está funcionando.", "No pudiste mirar: la cámara no funcionaba."
        if m[1] == "1":
            return f"Estás mirando a la cara {numero}.", f"Miraste a {nombre or f'la cara {numero}'}."
        return "Esa cara ya no está frente a la cámara.", f"La cara {numero} ya no estaba."
    if uso.name == "recordar_persona":
        nombre = str(datos.get("nombre", "")).strip()
        ropa = str(datos.get("ropa", "")).strip()
        vaciar_respuestas()
        avisar_ojos(f"P {nombre}")
        m = esperar_respuesta("P")
        notas = cargar_memoria()
        notas.append({"nota": f"{nombre}: la última vez llevaba {ropa}", "fecha": time.strftime("%Y-%m-%d")})
        guardar_memoria(notas)
        print(f"  (recordará a {nombre}: {ropa})")
        cara_ok = False
        if datos.get("guardar_cara"):
            vaciar_respuestas()
            avisar_ojos(f"H {nombre}")
            h = esperar_respuesta("H")
            cara_ok = h is not None and h[1] == "1"
            print(f"  (cara de {nombre}: {'guardada' if cara_ok else 'no se pudo ver bien'})")
        ropa_ok = m is not None and m[1] == "1"
        partes = []
        if cara_ok:
            partes.append("su cara")
        if ropa_ok:
            partes.append("su ropa")
        if not partes:
            return (f"Anotaste a {nombre}, pero la cámara no alcanzó a verlo bien para reconocerlo.",
                    f"Anotaste a {nombre} ({ropa}); la cámara no lo vio bien.")
        extra = "" if cara_ok or not datos.get("guardar_cara") else " (su cara no se vio bien: pídele que mire a la cámara y vuelve a intentarlo)"
        return (f"Ahora reconoces a {nombre} por {' y '.join(partes)}.{extra}",
                f"Recordaste a {nombre} por {' y '.join(partes)}: {ropa}.")
    if uso.name == "olvidar_persona":
        nombre = str(datos.get("nombre", "")).strip()
        avisar_ojos(f"X {nombre}")
        return f"Ya no reconoces a {nombre}: borraste su cara y su ropa.", f"Olvidaste a {nombre}."
    return "Esa herramienta no existe.", "Esa herramienta no existe."

# Frases que Whisper inventa con ruido o silencio
ALUCINACIONES = ("subtitulos", "gracias por ver", "suscribete", "amara.org")


class Estado:
    def __init__(self):
        self.modo = "iniciando"   # iniciando, escuchando, oyendo, pensando, hablando
        self.emocion, self.t_emocion = None, 0.0   # última emoción que dijo Claude, para la boca
        self.nivel_mic = 0.0
        self.nivel_voz = 0.0      # volumen de la voz del robot (1 = fuerte)
        self.agudeza = 0.0        # 0 vocal, 1 sonido tipo s/f
        self.voz_eco = 0.0        # volumen real reciente de su propia voz (para no confundirla)
        self.filtro_camara = True  # solo escucha a quien se ve hablando en la cámara (tecla C)
        self.quien = None          # quién habló en la última frase, según seguir.py
        self.ultimas_emociones = []  # para no reaccionar siempre igual
        self.umbral = 0.05        # volumen del micrófono desde el que cuenta como voz
        self.silenciado = False
        self.tu = ""
        self.robot = ""
        self.salir = False


estado = Estado()
ojos = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# Respuesta de seguir.py al terminar cada frase: si alguien frente a la cámara movía la boca
PUERTO_RESPUESTA = 47801
UMBRAL_VOZ_CAMARA = 0.25   # puntaje de boca acumulado en la frase para creer que habló alguien en cámara
respuestas = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
respuestas.bind(("127.0.0.1", PUERTO_RESPUESTA))
respuestas.setblocking(False)


def esperar_respuesta(tipo, espera=0.4):
    """Espera un mensaje de seguir.py que empiece con `tipo` ("A", "P", "M"). None si no llega."""
    limite = time.time() + espera
    while time.time() < limite:
        try:
            mensaje = respuestas.recv(256).decode().split(" ", 4)
        except BlockingIOError:
            time.sleep(0.01)
            continue
        if mensaje and mensaje[0] == tipo:
            return mensaje
    return None


def quien_hablo():
    """Pregunta a seguir.py quién habló en la frase que terminó. Devuelve None si seguir.py no
    contestó (entonces no se filtra), o {"hablo": si alguien en cámara movía la boca,
    "nombre": a quién se parece por la ropa (o None), "parecido": de 0 a 1}."""
    m = esperar_respuesta("A", 0.3)
    if m is None or len(m) < 3:
        return None
    puntaje, caras = float(m[1]), int(m[2])
    parecido = float(m[3]) if len(m) > 3 else 0.0
    etiqueta = m[4].strip() if len(m) > 4 else "-"
    fuente, _, nombre = etiqueta.partition(":") if ":" in etiqueta else ("ropa", "", etiqueta)
    nombre = nombre if nombre and nombre != "-" else None
    return {"hablo": caras > 0 and puntaje >= UMBRAL_VOZ_CAMARA, "nombre": nombre, "parecido": parecido,
            "fuente": fuente}


def mensaje_de_la_persona(texto, quien):
    """Lo que se le manda a Claude: la foto de quien habló (si la cámara lo marcó) y el texto con
    una nota de quién parece ser. Devuelve (contenido para Claude, texto para el historial)."""
    foto = CARPETA / "hablante.jpg"
    if not quien or not quien["hablo"] or not foto.exists() or time.time() - foto.stat().st_mtime > 5:
        return texto, texto
    if quien["nombre"] and quien.get("fuente") == "cara+ropa":
        nota = f"(La cámara marcó a quien te habló: por la cara y la ropa es {quien['nombre']}.)"
    elif quien["nombre"] and quien.get("fuente") == "cara":
        nota = f"(La cámara marcó a quien te habló: por la cara es {quien['nombre']}.)"
    elif quien["nombre"]:
        nota = f"(La cámara marcó a quien te habló: por la ropa parece ser {quien['nombre']}.)"
    else:
        nota = "(La cámara marcó a quien te habló: por la ropa no se parece a nadie que recuerdes.)"
    datos = base64.standard_b64encode(foto.read_bytes()).decode()
    contenido = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": datos}},
                 {"type": "text", "text": f"{nota}\n{texto}"}]
    return contenido, f"{nota}\n{texto}"


def vaciar_respuestas():
    try:
        while True:
            respuestas.recv(64)
    except BlockingIOError:
        pass


def sin_tildes(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def leer_clave():
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    archivo = CARPETA / "clave_anthropic.txt"
    if archivo.exists():
        os.environ["ANTHROPIC_API_KEY"] = archivo.read_text().strip()


def avisar_ojos(mensaje):
    # E n: expresión. V 1/0: alguien habla o no. R 1/0: el robot habla o no.
    ojos.sendto(mensaje.encode(), ("127.0.0.1", PUERTO_OJOS))


def expresion_ojos(numero):
    avisar_ojos(f"E {numero}")


def foto_para_claude():
    """La foto más reciente de la cámara como bloque de imagen, o un texto si no hay."""
    if not FOTO_CAMARA.exists() or time.time() - FOTO_CAMARA.stat().st_mtime > 5:
        return [{"type": "text", "text": "La cámara no está disponible ahora (seguir.py no está corriendo)."}]
    datos = base64.standard_b64encode(FOTO_CAMARA.read_bytes()).decode()
    return [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": datos}}]


def frases_de_claude(cliente, mensajes, resultado, cancelado):
    """Pide la respuesta en streaming y entrega cada oración apenas termina de llegar.
    Si Claude pide mirar, le pasa la foto de la cámara y sigue.
    Deja el texto completo en resultado["completo"]. Se detiene si `cancelado` se activa."""
    completo, pendiente = "", ""
    error = None
    mensajes = list(mensajes)
    # Las instrucciones (con la memoria) se arman una vez por turno: si cambiaran entre una vuelta
    # y otra de la misma respuesta, la API rechaza lo que Claude pensó en la vuelta anterior
    sistema = sistema_con_memoria()
    try:
        for _ronda in range(3):
            with cliente.messages.stream(
                model=MODELO,
                max_tokens=1024,
                system=sistema,
                messages=mensajes,
                tools=HERRAMIENTAS,
                output_config={"effort": "low"},
            ) as stream:
                for trozo in stream.text_stream:
                    if cancelado.is_set():
                        return
                    completo += trozo
                    resultado["completo"] = completo
                    pendiente += trozo
                    # Corta en fin de oración (seguido de espacio) o salto de línea
                    while (m := re.search(r"[.!?…](?=\s)|\n", pendiente)):
                        frase, pendiente = pendiente[:m.end()], pendiente[m.end():]
                        if frase.strip():
                            yield frase
                final = stream.get_final_message()
            if pendiente.strip():
                yield pendiente
                pendiente = ""
            if final.stop_reason != "tool_use" or cancelado.is_set():
                break
            # Claude pidió herramientas: mirar (lo dice en voz alta), recordar u olvidar
            usos = [b for b in final.content if b.type == "tool_use"]
            if any(u.name == "mirar" for u in usos):
                print("  (mirando por la cámara)")
                yield random.choice(MULETILLAS_MIRAR)
            resultados = []
            for u in usos:
                contenido, para_historial = usar_herramienta(u)
                resultados.append({"type": "tool_result", "tool_use_id": u.id, "content": contenido})
                resultado.setdefault("herramientas", []).append((u, para_historial))
            mensajes += [{"role": "assistant", "content": final.content},
                         {"role": "user", "content": resultados}]
        if final.stop_reason == "refusal" and not completo.strip():
            error = "Prefiero no responder eso."
    except anthropic.AuthenticationError:
        error = "No tengo una clave de API válida. Revisa el archivo clave anthropic punto t x t."
    except anthropic.RateLimitError:
        error = "Estoy recibiendo demasiadas preguntas. Dame un momento."
    except anthropic.APIConnectionError:
        error = "No me puedo conectar a internet."
    except anthropic.APIStatusError as e:
        print(f"Error de la API ({e.status_code}): {e.message}")
        error = "Tuve un problema para pensar la respuesta."

    if error:
        yield error


def separar_expresion(texto):
    """Quita las etiquetas [expresión] del texto y devuelve (texto, número o None)."""
    numero = None
    for etiqueta in re.findall(r"\[([^\]]+)\]", texto):
        nombre = sin_tildes(etiqueta.lower().strip())
        numero = EXPRESIONES.get(nombre)
        if numero:
            estado.ultimas_emociones = (estado.ultimas_emociones + [nombre])[-6:]
            estado.emocion, estado.t_emocion = nombre, time.time()
            break
    texto = re.sub(r"\[[^\]]*\]", "", texto)
    return re.sub(r"\s+", " ", texto).strip(), numero


class Voz(threading.Thread):
    """Mantiene cargada la voz del Mac en su propio hilo: así cada frase tarda ~0,1 s
    en vez de ~0,9 s que tarda `say` en cargarla cada vez."""

    def __init__(self):
        super().__init__(daemon=True)
        self.pedidos = queue.Queue()
        self.start()

    def run(self):
        try:
            from AppKit import NSSpeechSynthesizer
            from Foundation import NSDate, NSRunLoop, NSURL
            # La mejor calidad instalada de esa voz: premium, después mejorada, después compacta
            disponibles = [v for v in NSSpeechSynthesizer.availableVoices() if VOZ in v]
            nombre = next((v for calidad in ("premium", "enhanced", "compact", "")
                           for v in disponibles if calidad in v), None)
            if nombre is None:
                raise ValueError(f"no está instalada la voz {VOZ}")
            print(f"Voz: {nombre}")
            sintetizador = NSSpeechSynthesizer.alloc().initWithVoice_(nombre)
            sintetizador.setRate_(VELOCIDAD_VOZ / TONO)  # se reproduce más lenta: se genera más rápida
        except Exception as e:
            print(f"Uso `say` para la voz ({e})")
            sintetizador = None

        def a_archivo(texto, ruta):
            if sintetizador is None:
                subprocess.run(["say", "-v", VOZ_SAY, "-r", str(int(VELOCIDAD_VOZ / TONO)), "-o", ruta, texto],
                               check=True)
                return
            sintetizador.startSpeakingString_toURL_(texto, NSURL.fileURLWithPath_(ruta))
            while sintetizador.isSpeaking():
                NSRunLoop.currentRunLoop().runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(0.005))

        a_archivo("hola", tempfile.mktemp(suffix=".aiff"))  # la primera vez tarda más
        while True:
            texto, respuesta = self.pedidos.get()
            ruta = tempfile.mktemp(suffix=".aiff")
            a_archivo(texto, ruta)
            datos, tasa = sf.read(ruta, dtype="float32")
            os.unlink(ruta)
            # Reproducir a una tasa menor baja el tono (y alarga, por eso se generó más rápida)
            respuesta.put((datos.mean(axis=1) if datos.ndim > 1 else datos, int(tasa * TONO)))


voz = None


guardadas = {}  # voces ya generadas de las frases que se repiten (muletillas)


def sintetizar(texto, guardar=False):
    if texto in guardadas:
        return guardadas[texto]
    respuesta = queue.Queue(maxsize=1)
    voz.pedidos.put((texto, respuesta))
    audio = respuesta.get()
    if guardar:
        guardadas[texto] = audio
    return audio


def preparar_muletillas():
    for frase in MULETILLAS + MULETILLAS_LARGAS + MULETILLAS_MIRAR:
        sintetizar(separar_expresion(frase)[0], guardar=True)


def recortar(historial, maximo=24):
    """Los últimos mensajes del historial, empezando siempre en una pregunta de la persona
    (para no partir una mirada a la cámara por la mitad)."""
    recientes = historial[-maximo:]
    while recientes and not (recientes[0]["role"] == "user" and isinstance(recientes[0]["content"], str)):
        recientes = recientes[1:]
    return recientes


PALABRAS_PREGUNTA = ("que ", "como ", "por que", "cual", "quien", "donde", "cuando", "cuant", "sabes", "puedes",
                     "me dices", "me explicas", "crees", "te parece")


def es_pregunta(texto):
    """¿Le hicieron una pregunta? Solo entonces llena con muletillas la pausa en que piensa."""
    t = sin_tildes(texto.lower()).strip()
    return "?" in texto or t.startswith(PALABRAS_PREGUNTA) or any(f" {p}" in t for p in ("por que", "que opinas"))


def responder(cliente, historial, texto, fin_de_frase, sigue_hablando, ignorar_mic, alguien_interrumpe):
    """Habla la respuesta frase por frase: mientras dice una, prepara la voz de la siguiente.
    Si la respuesta se demora, dice muletillas.
    Devuelve False si se canceló porque la persona siguió hablando antes de que respondiera,
    "interrumpido" si alguien le habló mientras hablaba (se calla), y True si terminó."""
    expresion_ojos(PENSAR)
    cola = queue.Queue(maxsize=4)

    resultado = {"completo": ""}
    cancelado = threading.Event()
    contenido, texto_historial = mensaje_de_la_persona(texto, estado.quien)
    mensajes = recortar(historial) + [{"role": "user", "content": contenido}]

    def preparar():
        for frase in frases_de_claude(cliente, mensajes, resultado, cancelado):
            limpio, numero = separar_expresion(frase)
            cola.put((limpio, numero, sintetizar(limpio, guardar=frase in MULETILLAS_MIRAR) if limpio else None))
        cola.put(None)

    def decir_muletilla(opciones):
        frase = random.choice(opciones)
        print(f"Robot: {frase}  (muletilla)")
        estado.modo = "hablando"
        avisar_ojos("R 1")
        reproducir(*sintetizar(frase, guardar=True))
        avisar_ojos("R 0")
        estado.modo = "pensando"
        ignorar_mic()  # lo que oyó el micrófono era su propia voz

    threading.Thread(target=preparar, daemon=True).start()
    pregunta = es_pregunta(texto)
    primera, dicho, interrumpido = True, [], False
    silencio_desde, muletillas = time.time(), 0
    while True:
        try:
            item = cola.get(timeout=0.03)
        except queue.Empty:
            # Mientras todavía no empieza a responder, si la persona sigue hablando
            # se cancela la respuesta: quiere decir que no había terminado.
            if primera and sigue_hablando():
                cancelado.set()
                print("  (seguías hablando: espero a que termines)")
                return False
            # Si la respuesta se demora, llena la pausa como lo haría una persona
            espera = time.time() - silencio_desde
            if not pregunta:
                continue   # sin pregunta no hay muletillas: responde apenas tenga la respuesta
            if muletillas == 0 and espera > (ESPERA_MULETILLA if primera else ESPERA_MULETILLA_LARGA):
                decir_muletilla(MULETILLAS if primera else MULETILLAS_LARGAS)
                muletillas, silencio_desde = 1, time.time()
            elif muletillas == 1 and espera > ESPERA_MULETILLA_LARGA - ESPERA_MULETILLA:
                decir_muletilla(MULETILLAS_LARGAS)
                muletillas, silencio_desde = 2, time.time()
            continue
        if item is None:
            break
        limpio, numero, audio = item
        if primera:
            # Deja de "pensar" y mira a la persona (o hace la expresión de la frase)
            expresion_ojos(numero or 0)
            print(f"  (empezó a hablar {time.time() - fin_de_frase:.1f} s después de que terminaste)")
            primera = False
        elif numero:
            expresion_ojos(numero)
        if audio is not None:
            print(f"Robot: {limpio}" + (f"  [expresión {numero}]" if numero else ""))
            dicho.append(limpio)
            estado.robot = " ".join(dicho)
            estado.modo = "hablando"
            avisar_ojos("R 1")
            if not reproducir(*audio, interrumpe=alguien_interrumpe):
                print("  (me interrumpieron: me callo y escucho)")
                cancelado.set()
                interrumpido = True
                break
            silencio_desde, muletillas = time.time(), 0
    avisar_ojos("R 0")
    if primera:
        expresion_ojos(0)
    if resultado["completo"].strip() or dicho:
        historial.append({"role": "user", "content": texto_historial})
        for uso, para_historial in resultado.get("herramientas", []):
            # Queda registrado qué herramientas usó (sin la foto, que es cara de reenviar):
            # si no, en la próxima pregunta cree que inventó lo que vio.
            historial.append({"role": "assistant", "content": [
                {"type": "tool_use", "id": uso.id, "name": uso.name,
                 "input": uso.input if isinstance(uso.input, dict) else {}}]})
            historial.append({"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": uso.id, "content": para_historial}]})
        dicho_final = " ".join(dicho) + " (te interrumpieron aquí)" if interrumpido else (
            resultado["completo"].strip() or " ".join(dicho))
        historial.append({"role": "assistant", "content": dicho_final})
    return "interrumpido" if interrumpido else True


def reproducir(datos, tasa, interrumpe=None):
    """Reproduce con afplay (fuera de Python, así el audio no se entrecorta) y va
    moviendo la boca con el volumen y el tipo de sonido de cada instante.
    Si `interrumpe()` dice que alguien le habla, se calla y devuelve False."""
    paso = int(tasa * 0.01)  # trozos de 10 ms
    trozos = datos[:len(datos) // paso * paso].reshape(-1, paso)
    fuerza = np.sqrt((trozos ** 2).mean(axis=1))  # volumen real: sirve para estimar el eco
    volumen = fuerza / max(1e-6, np.percentile(fuerza, 95))
    # Cruces por cero: alto en sonidos como s, f, ch (boca estirada); bajo en vocales
    agudeza = (np.abs(np.diff(np.sign(trozos), axis=1)) > 0).mean(axis=1)
    agudeza = np.clip((agudeza - 0.05) / 0.25, 0, 1)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        ruta = f.name
    sf.write(ruta, datos, tasa)
    proceso = subprocess.Popen(["afplay", ruta])
    inicio = time.time()
    callado = False
    while proceso.poll() is None:
        i = int((time.time() - inicio) / 0.01)
        if i < len(volumen):
            estado.nivel_voz = float(volumen[i])
            estado.agudeza = float(agudeza[i])
        else:
            estado.nivel_voz = 0.0
        # Lo más fuerte que sonó en los últimos 150 ms: el eco llega al micrófono con algo de atraso
        estado.voz_eco = float(fuerza[max(0, i - 15):i + 1].max()) if i < len(fuerza) else 0.0
        if interrumpe and time.time() - inicio > 0.3 and interrumpe():
            proceso.terminate()
            callado = True
            break
        time.sleep(0.01)
    proceso.wait()
    os.unlink(ruta)
    estado.nivel_voz = estado.voz_eco = 0.0
    return not callado


def conversar():
    global voz
    os.environ.setdefault("HF_HOME", str(CARPETA / "modelos" / "hf"))
    import mlx_whisper

    voz = Voz()
    threading.Thread(target=preparar_muletillas, daemon=True).start()
    leer_clave()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Falta la clave de la API: ponla en clave_anthropic.txt o en ANTHROPIC_API_KEY")
    cliente = anthropic.Anthropic()

    def transcribir(audio):
        res = mlx_whisper.transcribe(audio, path_or_hf_repo=MODELO_WHISPER, language="es",
                                     initial_prompt=CONTEXTO_WHISPER,
                                     condition_on_previous_text=False)
        # Descarta los trozos que Whisper cree que no son voz
        return " ".join(s["text"] for s in res["segments"] if s.get("no_speech_prob", 0) < 0.6).strip()

    # La primera transcripción es más lenta: se hace una de prueba al arrancar
    transcribir(np.zeros(TASA, dtype="float32"))
    historial = []
    bloques = queue.Queue()

    def oir(entrada, _cuadros, _tiempo, _estado):
        bloques.put(entrada[:, 0].copy())

    try:
        microfono = sd.InputStream(samplerate=TASA, channels=1, blocksize=BLOQUE,
                                   dtype="float32", callback=oir)
        microfono.start()
    except Exception as e:
        print(f"No se pudo abrir el micrófono ({e}). ¿Falta el permiso en Privacidad y seguridad → Micrófono?")
        estado.modo = "error"
        return

    # Mide el ruido del ambiente para saber cuándo alguien habla
    muestras = [bloques.get() for _ in range(int(1.0 * TASA / BLOQUE))]
    piso = float(np.median([np.sqrt(np.mean(b ** 2)) for b in muestras]))
    guardado = CARPETA / "umbral_voz.txt"
    if guardado.exists():
        estado.umbral = float(guardado.read_text())
        print(f"Ruido ambiente {piso:.4f}, umbral de voz guardado {estado.umbral:.4f}. ¡Háblame!")
    else:
        estado.umbral = max(0.012, piso * 3.0)
        print(f"Ruido ambiente {piso:.4f}, umbral de voz {estado.umbral:.4f}. ¡Háblame!")
    print("Puedes cambiar el umbral con el deslizable de la ventana de la boca (o ↑ ↓).")

    previo, grabando, silencio, voz_seguida = [], [], 0, 0
    texto_previo = ""     # lo que se alcanzó a decir antes de una pausa larga
    retenidos = []        # bloques que se escucharon mientras pensaba la respuesta

    def ignorar_mic():
        time.sleep(0.15)
        while not bloques.empty():
            bloques.get_nowait()

    eco = {"razones": [], "ultimos": []}
    recientes = []

    def alguien_interrumpe():
        """Mientras el robot habla: ¿alguien le está hablando? En un notebook el micrófono capta
        mucho la voz del propio robot (eco), así que aprende cuánto llega y solo cuenta:
          - en las pausas del robot (su eco casi desaparece): voz sobre el umbral normal
          - mientras suena: algo bastante más fuerte que el eco más alto que suele llegar."""
        hay = False
        while not bloques.empty():
            b = bloques.get_nowait()
            recientes.append(b)
            del recientes[:-20]
            mic = float(np.sqrt(np.mean(b ** 2)))
            propia = estado.voz_eco
            if propia > 0.01:
                eco["razones"].append(mic / propia)
                del eco["razones"][:-400]
            if len(eco["razones"]) < 30:
                continue  # todavía no sabe cuánto eco llega: no se arriesga
            if propia < 0.01:
                fuerte = mic > estado.umbral
            else:
                eco_alto = float(np.percentile(eco["razones"], 90))
                fuerte = mic > max(estado.umbral, 1.8 * eco_alto * propia)
            eco["ultimos"] = (eco["ultimos"] + [fuerte])[-10:]
            if sum(eco["ultimos"]) >= 6:  # 6 de los últimos 10 (~0,3 s)
                eco["ultimos"] = []
                retenidos[:] = list(recientes)
                hay = True
        return hay

    def sigue_hablando():
        """Revisa el micrófono mientras el robot piensa: ¿la persona volvió a hablar?"""
        seguidos = 0
        while not bloques.empty():
            b = bloques.get_nowait()
            retenidos.append(b)
            seguidos = seguidos + 1 if np.sqrt(np.mean(b ** 2)) > estado.umbral else 0
            if seguidos >= 5:
                return True
        return False

    estado.modo = "escuchando"
    archivo_saludar = CARPETA / "saludar"
    archivo_saludar.unlink(missing_ok=True)
    archivo_decir = CARPETA / "decir"            # frases de seguir.py (escaneo de cara)
    archivo_escaneo = CARPETA / "escaneando"     # mientras escanea no conversa
    archivo_decir.unlink(missing_ok=True)
    while not estado.salir:
        # Se despertó porque apareció alguien: lo saluda (si no está oyendo a nadie)
        if not grabando and not texto_previo and archivo_saludar.exists():
            nombre = archivo_saludar.read_text().strip()
            archivo_saludar.unlink(missing_ok=True)
            quien = f" (por la ropa parece ser {nombre})" if nombre else ""
            aviso = ("[Estabas durmiendo porque no había nadie y acabas de despertar: apareció alguien "
                     f"frente a ti{quien}. Salúdalo con una frase corta y natural, como recién despertando.]")
            print(f"Despertó: saluda{quien}")
            estado.quien = None
            estado.tu, estado.robot = "", ""
            responder(cliente, historial, aviso, time.time(), sigue_hablando, ignorar_mic, alguien_interrumpe)
            time.sleep(0.3)
            while not bloques.empty():
                bloques.get_nowait()
            estado.modo = "escuchando"
            continue
        # seguir.py pide decir una frase tal cual (instrucciones del escaneo de cara)
        if archivo_decir.exists():
            frase = archivo_decir.read_text().strip()
            archivo_decir.unlink(missing_ok=True)
            if frase:
                print(f"Robot: {frase}  (escaneo)")
                estado.robot, estado.modo = frase, "hablando"
                avisar_ojos("R 1")
                reproducir(*sintetizar(frase))
                avisar_ojos("R 0")
                ignorar_mic()
                while not bloques.empty():
                    bloques.get_nowait()
                previo, grabando, texto_previo = [], [], ""
                estado.modo = "escuchando"
        b = bloques.get()
        nivel = float(np.sqrt(np.mean(b ** 2)))
        estado.nivel_mic = nivel
        avisar_ojos(f"N {nivel:.4f}")  # para saber qué boca se mueve con el sonido

        if estado.silenciado or ARCHIVO_DORMIDO.exists() or archivo_escaneo.exists():   # dormido no escucha: solo lo despierta ver a alguien
            previo, grabando, texto_previo = [], [], ""
            estado.modo = "escuchando"
            continue

        if not grabando:
            previo = (previo + [b])[-10:]
            voz_seguida = voz_seguida + 1 if nivel > estado.umbral else 0
            if voz_seguida >= 3:
                grabando, silencio = list(previo), 0
                estado.modo = "oyendo"
                avisar_ojos("V 1")
            continue

        grabando.append(b)
        silencio = silencio + 1 if nivel < estado.umbral * 0.7 else 0
        if silencio * BLOQUE / TASA < SILENCIO_FINAL and len(grabando) * BLOQUE / TASA < DURACION_MAXIMA:
            continue

        # Terminó la frase
        vaciar_respuestas()
        avisar_ojos("V 0")
        fin_de_frase = time.time() - silencio * BLOQUE / TASA
        estado.quien = quien_hablo()
        if estado.filtro_camara and estado.quien and not estado.quien["hablo"] and not texto_previo:
            # Nadie frente a la cámara movía la boca: era una voz del fondo
            print("  (voz del fondo: nadie frente a la cámara estaba hablando, la ignoro)")
            previo, grabando, voz_seguida = [], [], 0
            estado.modo = "escuchando"
            continue
        audio = np.concatenate(grabando)
        previo, grabando, voz_seguida = [], [], 0
        estado.modo = "pensando"
        texto = transcribir(audio)
        if len(texto) < 2 or any(a in sin_tildes(texto.lower()) for a in ALUCINACIONES):
            if not texto_previo:
                estado.modo = "escuchando"
                continue
            texto = ""  # solo ruido: responde a lo que ya había dicho
        texto = f"{texto_previo} {texto}".strip()

        print(f"Tú: {texto}  (entendido en {time.time() - fin_de_frase:.1f} s)")
        estado.tu, estado.robot = texto, ""
        retenidos.clear()
        resultado_respuesta = responder(cliente, historial, texto, fin_de_frase, sigue_hablando, ignorar_mic,
                                        alguien_interrumpe)
        if resultado_respuesta == "interrumpido":
            # Le hablaron mientras hablaba: escucha lo nuevo desde lo que alcanzó a oír
            texto_previo = ""
            grabando, silencio = list(retenidos), 0
            estado.modo = "oyendo"
            avisar_ojos("V 1")
            continue
        if not resultado_respuesta:
            # Siguió hablando: retoma la grabación con lo que se escuchó y junta los textos
            texto_previo = texto
            grabando, silencio = list(retenidos), 0
            estado.modo = "oyendo"
            avisar_ojos("V 1")
            continue
        texto_previo = ""

        # Descarta lo que el micrófono oyó mientras hablaba (su propia voz)
        time.sleep(0.3)
        while not bloques.empty():
            bloques.get_nowait()
        estado.modo = "escuchando"


def curva(p0, p1, p2, n=40):
    """Puntos de una curva de Bézier cuadrática."""
    return [((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * p1[0] + u ** 2 * p2[0],
             (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * p1[1] + u ** 2 * p2[1])
            for u in (i / (n - 1) for i in range(n))]


def dibujar_forma_boca(pantalla, ancho, alto, forma, color_labios):
    """Boca de caricatura: labios, interior oscuro, dientes arriba y lengua abajo."""
    W = min(ancho * 0.45, alto * 1.1) * forma["ancho"]
    cx = ancho / 2 + forma["lado"] * ancho
    cy = alto * 0.45
    abierta = W * 0.38 * forma["abierta"]
    subida = W * 0.16 * forma["sonrisa"]         # las comisuras suben al sonreír
    ladeo = W * 0.12 * forma["ladeo"]            # una comisura más arriba que la otra
    izq, der = (cx - W / 2, cy - subida + ladeo), (cx + W / 2, cy - subida - ladeo)
    grosor = max(8, int(W * 0.055))

    if abierta < 3:
        # Cerrada: una sola curva, sonriente o no
        linea = curva(izq, (cx, cy + subida * 1.5), der)
        pygame.draw.lines(pantalla, color_labios, False, linea, grosor)
        for p in (izq, der):
            pygame.draw.circle(pantalla, color_labios, p, grosor / 2)
        return

    arriba = curva(izq, (cx, cy - abierta * 0.7 + subida * 0.6), der)
    abajo = curva(der, (cx, cy + abierta * 2.0 + subida * 1.4), izq)
    contorno = arriba + abajo

    # Se dibuja en una superficie del tamaño de la boca para poder recortar
    # los dientes y la lengua al interior
    x0 = int(min(p[0] for p in contorno)) - grosor
    y0 = int(min(p[1] for p in contorno)) - grosor
    w = int(max(p[0] for p in contorno)) - x0 + grosor * 2
    h = int(max(p[1] for p in contorno)) - y0 + grosor * 2
    local = [(p[0] - x0, p[1] - y0) for p in contorno]
    interior = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.polygon(interior, (55, 12, 22), local)

    detalle = pygame.Surface((w, h), pygame.SRCALPHA)
    alto_dientes = min(abierta * 0.28, W * 0.06)
    dientes = [(p[0] - x0, p[1] - y0) for p in arriba]
    dientes += [(x, y + alto_dientes) for x, y in reversed(dientes)]
    pygame.draw.polygon(detalle, (245, 242, 235), dientes)
    if abierta > W * 0.1:
        lengua = pygame.Rect(0, 0, W * 0.55, abierta * 1.0)
        lengua.center = (cx - x0, cy + abierta * 1.15 + subida * 0.5 - y0)
        pygame.draw.ellipse(detalle, (225, 85, 105), lengua)
    mascara = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.polygon(mascara, (255, 255, 255, 255), local)
    detalle.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    interior.blit(detalle, (0, 0))
    pantalla.blit(interior, (x0, y0))

    for labio in (arriba, abajo):
        pygame.draw.lines(pantalla, color_labios, False, labio, grosor)
    for p in (izq, der):
        pygame.draw.circle(pantalla, color_labios, p, grosor / 2)


ARCHIVO_DORMIDO = CARPETA / "durmiendo"   # lo crea seguir.py cuando no ve a nadie hace rato
CICLO_RONQUIDO = 3.6                      # segundos de cada respiración


def ronquido(t):
    """Apertura de la boca al roncar (0 a 1): inspira despacio y bota el aire de golpe."""
    f = (t % CICLO_RONQUIDO) / CICLO_RONQUIDO
    return f / 0.7 if f < 0.7 else max(0.0, 1 - (f - 0.7) / 0.12)


def dibujar_zetas(pantalla, ancho, alto, t, letras):
    """Zetas que salen de la boca y suben flotando mientras duerme."""
    cx, cy = ancho / 2, alto * 0.45
    W = min(ancho * 0.45, alto * 1.1)
    for k in range(5):
        f = (t / (CICLO_RONQUIDO * 2.5) + k / 5) % 1           # avance de cada z (0 a 1)
        tam = int(14 + 40 * f)
        letra = letras.get(tam)
        if letra is None:
            letra = letras[tam] = pygame.font.SysFont("Helvetica", tam, bold=True)
        z = letra.render("z" if k % 2 else "Z", True, (255, 125, 30))
        z.set_alpha(int(255 * min(1, f * 4) * (1 - f)))
        x = cx + W * 0.42 + f * W * 0.45 + 10 * math.sin(t * 2 + k)
        y = cy - W * 0.05 - f * alto * 0.38
        pantalla.blit(z, z.get_rect(center=(x, y)))


# Forma de la boca para cada emoción (se mezcla con el habla: la apertura la sigue dando la voz)
FORMAS_EMOCION = {
    "feliz": {"sonrisa": 0.8},
    "sorpresa": {"ancho": 0.5, "sonrisa": 0.0, "abre": 0.45},
    "sorprendido": {"ancho": 0.5, "sonrisa": 0.0, "abre": 0.45},
    "triste": {"sonrisa": -0.6, "ancho": 0.85},
    "enojo": {"sonrisa": -0.35, "ancho": 0.8, "ladeo": 0.0},
    "enojado": {"sonrisa": -0.35, "ancho": 0.8, "ladeo": 0.0},
    "sospecha": {"sonrisa": 0.05, "ladeo": 0.35, "lado": -0.05},
    "sarcastico": {"sonrisa": 0.4, "ladeo": 0.55, "lado": 0.06},
    "rodar": {"sonrisa": 0.4, "ladeo": 0.55, "lado": 0.06},
    "guino": {"sonrisa": 0.6, "ladeo": 0.3},
    "curioso": {"ancho": 0.65, "abre": 0.15},
    "confundido": {"sonrisa": -0.1, "ladeo": "duda", "lado": 0.05},
    "nervioso": {"sonrisa": 0.1, "ancho": 0.8, "ladeo": "tiembla"},
    "sueno": {"ancho": 0.75, "sonrisa": -0.1},
    "cansado": {"ancho": 0.75, "sonrisa": -0.1},
    "pensativo": {"ancho": 0.55, "sonrisa": 0.05, "lado": 0.12, "ladeo": 0.35},
    "pensar": {"ancho": 0.55, "sonrisa": 0.05, "lado": 0.12, "ladeo": 0.35},
}
DURA_EMOCION = 4.0   # segundos que la boca mantiene la emoción después de decirla


def aplicar_emocion(objetivo, emocion, t, hablando):
    forma = FORMAS_EMOCION.get(emocion)
    if not forma:
        return
    for clave, valor in forma.items():
        if valor == "duda":
            valor = -0.35 + 0.15 * math.sin(t * 4)
        elif valor == "tiembla":
            valor = 0.08 * math.sin(t * 25)
        if clave == "abre":
            if not hablando:
                objetivo["abierta"] = max(objetivo["abierta"], valor)
        else:
            objetivo[clave] = valor


MAXIMO_DESLIZABLE = 0.3  # volumen del micrófono en el extremo derecho del deslizable


def a_posicion(valor):
    # Escala de raíz: da más espacio a los volúmenes bajos, que son los que importan
    return math.sqrt(min(1.0, max(0.0, valor / MAXIMO_DESLIZABLE)))


def de_posicion(fraccion):
    return MAXIMO_DESLIZABLE * min(1.0, max(0.0, fraccion)) ** 2


def dibujar_deslizable(pantalla, rect, nivel, umbral, letra):
    """Barra con el volumen del micrófono en vivo y una marca para el umbral de voz."""
    pygame.draw.rect(pantalla, (40, 40, 48), rect, border_radius=6)
    lleno = rect.copy()
    lleno.width = int(rect.width * a_posicion(nivel))
    pygame.draw.rect(pantalla, (90, 230, 150) if nivel > umbral else (110, 110, 125), lleno, border_radius=6)
    x = rect.x + rect.width * a_posicion(umbral)
    pygame.draw.line(pantalla, (255, 255, 255), (x, rect.y - 6), (x, rect.bottom + 6), 3)
    texto = letra.render(f"umbral de voz {umbral:.3f}  (arrástralo, o usa las flechas)", True, (170, 170, 180))
    pantalla.blit(texto, (rect.x, rect.bottom + 8))


def dibujar_boca():
    pygame.init()
    pantalla = pygame.display.set_mode((1000, 420), pygame.RESIZABLE)
    pygame.display.set_caption("Boca")
    reloj = pygame.time.Clock()
    letra = pygame.font.SysFont("Helvetica", 26)
    letra_chica = pygame.font.SysFont("Helvetica", 16)
    letras_z = {}
    durmiendo, revisado = False, 0.0
    subtitulos = True
    ver_deslizable = True
    arrastrando = False
    nivel_visto = 0.0  # volumen del micrófono suavizado para la barra
    deslizable = pygame.Rect(20, 50, 280, 12)
    inicio = time.time()

    def guardar_umbral():
        (CARPETA / "umbral_voz.txt").write_text(f"{estado.umbral:.4f}")
    # Forma actual de la boca (se suaviza hacia la forma objetivo en cada cuadro)
    forma = {"abierta": 0.0, "ancho": 1.0, "sonrisa": 0.3, "lado": 0.0, "ladeo": 0.0}
    web_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)   # boca para la página (puerto 47802)
    cuadro_web = 0

    # Puntito de estado en la esquina
    colores = {
        "iniciando": (90, 90, 110),
        "escuchando": (70, 190, 255),
        "oyendo": (90, 255, 170),
        "pensando": (170, 120, 255),
        "hablando": (255, 140, 40),
        "error": (255, 60, 60),
    }

    while not estado.salir:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                estado.salir = True
            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    estado.salir = True
                elif evento.key == pygame.K_f:
                    pygame.display.toggle_fullscreen()
                elif evento.key == pygame.K_m:
                    estado.silenciado = not estado.silenciado
                elif evento.key == pygame.K_s:
                    subtitulos = not subtitulos
                elif evento.key == pygame.K_c:
                    estado.filtro_camara = not estado.filtro_camara
                    print("Filtro de voces del fondo:", "activado" if estado.filtro_camara else "desactivado")
                elif evento.key == pygame.K_u:
                    ver_deslizable = not ver_deslizable
                elif evento.key in (pygame.K_UP, pygame.K_DOWN):
                    paso = 0.03 if evento.key == pygame.K_UP else -0.03
                    estado.umbral = de_posicion(a_posicion(estado.umbral) + paso)
                    guardar_umbral()
            elif evento.type == pygame.MOUSEBUTTONDOWN and ver_deslizable \
                    and deslizable.inflate(20, 30).collidepoint(evento.pos):
                arrastrando = True
            elif evento.type == pygame.MOUSEBUTTONUP and arrastrando:
                arrastrando = False
                guardar_umbral()
            if arrastrando and evento.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION):
                estado.umbral = max(0.002, de_posicion((evento.pos[0] - deslizable.x) / deslizable.width))

        ancho, alto = pantalla.get_size()
        t_real = time.time()
        t = t_real - inicio
        modo = estado.modo
        if t - revisado > 0.5:   # seguir.py avisa con un archivo que se durmió
            durmiendo, revisado = ARCHIVO_DORMIDO.exists(), t
        dormida = durmiendo and modo in ("escuchando", "iniciando")

        # Forma objetivo según lo que está haciendo
        objetivo = {"abierta": 0.0, "ancho": 1.0 + 0.01 * math.sin(t * 1.5), "sonrisa": 0.35,
                    "lado": 0.0, "ladeo": 0.0}
        if dormida:   # roncando: boca redonda que se abre al inspirar y se cierra al botar el aire
            r = ronquido(t)
            objetivo.update(abierta=0.15 + 0.8 * r, ancho=0.32 + 0.1 * r, sonrisa=-0.05,
                            lado=0.0, ladeo=0.05 * math.sin(t * 0.7))
        elif estado.silenciado:
            objetivo["sonrisa"] = 0.0
        elif modo == "hablando":
            abrir = min(1.0, estado.nivel_voz * 0.8)
            objetivo["abierta"] = abrir * (1 - 0.45 * estado.agudeza)    # s, f: casi cerrada
            objetivo["ancho"] = 1.0 - 0.22 * abrir + 0.12 * estado.agudeza  # a, o: redonda
            objetivo["sonrisa"] = 0.25
        elif modo == "oyendo":
            objetivo["sonrisa"] = 0.6
        elif modo == "pensando":  # "mmm" hacia un lado
            objetivo.update(ancho=0.55, sonrisa=0.05, lado=0.12,
                            ladeo=0.35 + 0.15 * math.sin(t * 3))
        elif modo == "error":
            objetivo["sonrisa"] = -0.5
        # La emoción de lo que dice (mientras habla y un rato después)
        if not dormida and estado.emocion and (modo == "hablando" or t_real - estado.t_emocion < DURA_EMOCION):
            aplicar_emocion(objetivo, estado.emocion, t, modo == "hablando")
        for clave, valor in objetivo.items():
            rapidez = 0.6 if clave == "abierta" and valor > forma[clave] else 0.3
            forma[clave] += (valor - forma[clave]) * rapidez
        # La misma boca, para el panel de la página (servidor.py la reenvía al navegador)
        cuadro_web += 1
        if cuadro_web % 3 == 0:
            try:
                web_udp.sendto(json.dumps({
                    "forma": {k: round(v, 3) for k, v in forma.items()}, "modo": modo, "dormida": dormida,
                    "silenciado": estado.silenciado, "tu": estado.tu[-160:], "robot": estado.robot[-220:],
                    "emocion": estado.emocion, "mic": round(estado.nivel_mic, 4), "umbral": round(estado.umbral, 4),
                }, ensure_ascii=False).encode()[:8000], ("127.0.0.1", 47802))
            except OSError:
                pass

        pantalla.fill((0, 0, 0))
        dibujar_forma_boca(pantalla, ancho, alto - (70 if subtitulos else 0), forma,
                           (120, 120, 120) if estado.silenciado else (255, 125, 30))
        pygame.draw.circle(pantalla, colores.get(modo, (200, 200, 200)), (ancho - 24, 24), 7)
        if dormida:
            dibujar_zetas(pantalla, ancho, alto - (70 if subtitulos else 0), t, letras_z)

        if subtitulos:
            for k, (texto, tono) in enumerate(((estado.robot, (230, 230, 230)), (estado.tu, (120, 120, 130)))):
                if texto:
                    linea = letra.render(texto[-110:], True, tono)
                    pantalla.blit(linea, linea.get_rect(center=(ancho / 2, alto - 30 - 34 * k)))
        if estado.silenciado:
            aviso = letra.render("micrófono silenciado (M)", True, (150, 150, 150))
            pantalla.blit(aviso, (20, 90 if ver_deslizable else 16))
        if ver_deslizable:
            # Sube rápido y baja despacio, para que se alcance a leer
            nivel_visto = max(estado.nivel_mic, nivel_visto * 0.9)
            dibujar_deslizable(pantalla, deslizable, nivel_visto, estado.umbral, letra_chica)
            filtro = letra_chica.render(
                "solo escucha a quien se ve hablando (C)" if estado.filtro_camara else "escucha todas las voces (C)",
                True, (170, 170, 180))
            pantalla.blit(filtro, (deslizable.x, deslizable.bottom + 30))

        pygame.display.flip()
        reloj.tick(60)
    pygame.quit()


if __name__ == "__main__":
    threading.Thread(target=conversar, daemon=True).start()
    dibujar_boca()
