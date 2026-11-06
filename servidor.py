# Servidor local de la página: sirve web/ y deja manejar el robot desde Chrome.
#   http://localhost:8730          la página (con el panel de control)
#   POST /api/iniciar              cierra lo anterior y abre seguir.py (cámara) y hablar.py (voz)
#   POST /api/detener              cierra los dos (los ojos vuelven a moverse solos)
#   POST /api/expresion?n=7        expresión en el robot real
#   POST /api/escanear  {nombre}   escaneo guiado de una cara (con permiso de la persona)
#   POST /api/cancelar_escaneo
#   GET  /api/vivo                 eventos en vivo: la boca (20 por segundo) y el estado (2 por segundo)
#   GET  /api/camara.jpg           la imagen de la cámara con las caras marcadas
# Solo escucha en 127.0.0.1: desde otro computador no se puede usar.
# Uso: .venv/bin/python servidor.py   (o doble clic en pagina.command)
import json, os, signal, socket, subprocess, threading, time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

RAIZ = Path(__file__).resolve().parent
WEB = RAIZ / "web"
PUERTO = 8730
PUERTO_OJOS = 47800        # seguir.py escucha órdenes aquí
PUERTO_BOCA = 47802        # hablar.py manda aquí la forma de la boca en cada cuadro
PYTHON = str(RAIZ / ".venv" / "bin" / "python")
ESTADO_SEGUIR = RAIZ / "estado_seguir.json"
CAMARA = RAIZ / "vista_web.jpg"
REGISTRO_HABLAR = RAIZ / "registro_hablar.txt"
AVISOS = ("durmiendo", "saludar", "decir", "escaneando")

boca = {"t": 0.0}
procesos = {}
iniciando = {"hasta": 0.0}
ojos_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def escuchar_boca():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", PUERTO_BOCA))
    while True:
        try:
            datos = json.loads(s.recv(8192).decode())
            datos["t"] = time.time()
            boca.clear(); boca.update(datos)
        except Exception:
            pass


def corriendo(nombre):
    return subprocess.run(["pgrep", "-f", f"[{nombre[0]}]{nombre[1:]}.py"], capture_output=True).returncode == 0


def cerrar(nombre, suave=True):
    patron = f"[{nombre[0]}]{nombre[1:]}.py"
    if suave:   # Ctrl+C: seguir.py alcanza a dejar los ojos animados y soltar la cámara
        subprocess.run(["pkill", "-INT", "-f", patron])
        for _ in range(30):
            if not corriendo(nombre):
                return
            time.sleep(0.1)
    subprocess.run(["pkill", "-9", "-f", patron])


def abrir(nombre, args):
    registro = open(RAIZ / f"registro_{nombre}.txt", "w")
    procesos[nombre] = subprocess.Popen([PYTHON, "-u", f"{nombre}.py", *args], cwd=RAIZ, stdout=registro,
                                        stderr=subprocess.STDOUT, start_new_session=True)


def iniciar():
    iniciando["hasta"] = time.time() + 25
    for n in ("hablar", "seguir"):
        cerrar(n)
    for a in AVISOS:
        (RAIZ / a).unlink(missing_ok=True)
    abrir("seguir", ["--ventana"])
    time.sleep(7)              # que la cámara y el Arduino partan antes que la voz
    abrir("hablar", [])
    iniciando["hasta"] = time.time() + 12   # Whisper tarda unos segundos en cargar


def detener():
    iniciando["hasta"] = 0
    for n in ("hablar", "seguir"):
        cerrar(n)
    for a in AVISOS:
        (RAIZ / a).unlink(missing_ok=True)
    ESTADO_SEGUIR.unlink(missing_ok=True)
    CAMARA.unlink(missing_ok=True)


def conversacion(maximo=14):
    try:
        lineas = REGISTRO_HABLAR.read_text(errors="ignore").splitlines()
    except FileNotFoundError:
        return []
    salida = []
    for l in lineas:
        if l.startswith("Tú: "):
            salida.append({"quien": "tu", "texto": l[4:].split("  (entendido")[0]})
        elif l.startswith("Robot: "):
            texto = l[7:].split("  [expresión")[0].split("  (muletilla)")[0].split("  (escaneo)")[0]
            salida.append({"quien": "robot", "texto": texto})
    return salida[-maximo:]


def estado():
    ahora = time.time()
    seguir = None
    try:
        if ahora - ESTADO_SEGUIR.stat().st_mtime < 3:
            seguir = json.loads(ESTADO_SEGUIR.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    corre = {"seguir": corriendo("seguir"), "hablar": corriendo("hablar")}
    return {"corriendo": corre, "iniciando": ahora < iniciando["hasta"] and not (seguir and boca.get("t", 0) > ahora - 2),
            "seguir": seguir, "conversacion": conversacion(),
            "camara": CAMARA.exists() and ahora - CAMARA.stat().st_mtime < 3}


class Manejador(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(WEB), **k)

    def log_message(self, *_):
        pass

    def end_headers(self):
        if not self.path.startswith("/api/"):
            self.send_header("Cache-Control", "no-cache")   # siempre la última versión de la página
        super().end_headers()

    def json(self, datos, codigo=200):
        cuerpo = json.dumps(datos, ensure_ascii=False).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        ruta = urlparse(self.path).path
        if ruta == "/api/estado":
            return self.json(estado())
        if ruta == "/api/camara.jpg":
            try:
                datos = CAMARA.read_bytes()
            except FileNotFoundError:
                self.send_response(404); self.end_headers(); return
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            self.wfile.write(datos)
            return
        if ruta == "/api/vivo":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            ultimo_estado = 0.0
            try:
                while True:
                    ahora = time.time()
                    if ahora - boca.get("t", 0) < 2:
                        self.wfile.write(f"event: boca\ndata: {json.dumps(boca, ensure_ascii=False)}\n\n".encode())
                    if ahora - ultimo_estado > 0.5:
                        ultimo_estado = ahora
                        self.wfile.write(f"event: estado\ndata: {json.dumps(estado(), ensure_ascii=False)}\n\n".encode())
                    self.wfile.flush()
                    time.sleep(0.05)
            except (BrokenPipeError, ConnectionResetError):
                return
        return super().do_GET()

    def do_POST(self):
        # Solo la propia página: los otros sitios no pueden mandar este encabezado sin permiso
        if self.headers.get("X-Robot") != "1":
            return self.json({"error": "no permitido"}, 403)
        url = urlparse(self.path)
        largo = int(self.headers.get("Content-Length") or 0)
        cuerpo = json.loads(self.rfile.read(largo) or b"{}") if largo else {}
        if url.path == "/api/iniciar":
            threading.Thread(target=iniciar, daemon=True).start()
            return self.json({"ok": True})
        if url.path == "/api/detener":
            threading.Thread(target=detener, daemon=True).start()
            return self.json({"ok": True})
        if url.path == "/api/expresion":
            n = int(parse_qs(url.query).get("n", ["0"])[0])
            ojos_udp.sendto(f"E {max(0, min(16, n))}".encode(), ("127.0.0.1", PUERTO_OJOS))
            return self.json({"ok": True})
        if url.path == "/api/escanear":
            nombre = "".join(ch for ch in str(cuerpo.get("nombre", "")) if ch.isprintable()).strip()[:40]
            if not nombre:
                return self.json({"error": "falta el nombre"}, 400)
            ojos_udp.sendto(f"S {nombre}".encode(), ("127.0.0.1", PUERTO_OJOS))
            return self.json({"ok": True})
        if url.path == "/api/cancelar_escaneo":
            ojos_udp.sendto(b"S-", ("127.0.0.1", PUERTO_OJOS))
            return self.json({"ok": True})
        return self.json({"error": "no existe"}, 404)


if __name__ == "__main__":
    threading.Thread(target=escuchar_boca, daemon=True).start()
    servidor = ThreadingHTTPServer(("127.0.0.1", PUERTO), Manejador)
    servidor.daemon_threads = True
    print(f"Página del robot en http://localhost:{PUERTO}  (Ctrl+C para apagar la página)")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
