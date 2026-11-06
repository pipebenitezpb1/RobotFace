# Envía órdenes al Arduino por serie y muestra las respuestas.
# Uso: python3 serie.py "orden1" "orden2" ...
import glob, os, sys, termios, time, select

PUERTO = next(iter(sorted(glob.glob("/dev/cu.usbmodem*") + glob.glob("/dev/cu.usbserial*"))))

fd = os.open(PUERTO, os.O_RDWR | os.O_NOCTTY)
attr = termios.tcgetattr(fd)
attr[0] = 0; attr[1] = 0
attr[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
attr[3] = 0
attr[4] = attr[5] = termios.B115200
termios.tcsetattr(fd, termios.TCSANOW, attr)

def leer(segundos, hasta_linea=False):
    # Con hasta_linea, vuelve en cuanto llega una respuesta completa
    fin, datos = time.time() + segundos, b""
    while time.time() < fin:
        r, _, _ = select.select([fd], [], [], 0.01)
        if r:
            datos += os.read(fd, 1024)
            if hasta_linea and datos.endswith(b"\n"):
                break
    return datos.decode(errors="replace")

print(leer(2.5), end="")  # al abrir el puerto el Uno se reinicia
for orden in sys.argv[1:]:
    if orden.startswith("espera"):
        time.sleep(float(orden.split()[1]))
        continue
    os.write(fd, (orden + "\n").encode())
    print(leer(0.6, hasta_linea=orden != "c"), end="")
os.close(fd)
