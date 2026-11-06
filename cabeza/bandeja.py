# Bandeja y carcasa para el EyeMech ε3.2 sobre cualquier pantalla, hechas a partir de la base
# real del mecanismo (cabeza/eyemech_base.stl, sacada del 3MF oficial de Will Cogley).
# La bandeja va sobre el borde de la pantalla, casi toda por detrás, con los ojos al ras del frente
# de la pantalla. Se sujeta con dos ganchos adelante y un brazo pivotante atrás, que se imprimen
# aparte y se encajan después en ranuras de cola de milano bajo la bandeja:
#   gancho.stl (x2)  pasan sobre el borde de la pantalla y bajan por delante, a los lados de la cámara
#   soporte_brazo.stl + brazo.stl  el brazo se apoya atrás de la pantalla y da el ángulo (tornillo M3)
#
# Uso:  .venv-cad/bin/python cabeza/bandeja.py            genera los STL en cabeza/stl_bandeja/
#       .venv-cad/bin/python cabeza/bandeja.py --revisar  además revisa choques y la cámara
#
# Ejes: z hacia arriba, y hacia adelante (hacia la persona), x a los lados. Milímetros.
# z=0 es la cara de arriba de la bandeja; y=0 es el frente de la pantalla.
import math
import sys
from pathlib import Path
import cadquery as cq

sys.path.insert(0, str(Path(__file__).parent))
import pantallas as mm       # pantallas de ejemplo y la cámara

# ---------------- El mecanismo, medido en sus piezas y confirmado con fotos -------------------
# "Base frame": bx de 0 a 145.4 (izquierda a derecha), by de 0 (borde de adelante) a 95 (atrás).
BASE_ANCHO, BASE_FONDO = 145.4, 95.0
BASE_GROSOR = 5.0
# Contorno de la base: envolvente de la pieza real (esquinas de atrás cortadas en diagonal)
CONTORNO_BASE = [(6.0, 0.0), (3.7, 0.46), (1.76, 1.76), (0.46, 3.7), (0.01, 5.74), (0.01, 73.53), (0.27, 75.05), (0.92, 76.46), (1.91, 77.66), (3.18, 78.56), (32.68, 94.29), (34.52, 94.92), (109.9, 95.0), (111.36, 94.82), (112.72, 94.29), (142.22, 78.56), (143.67, 77.48), (144.61, 76.24), (145.2, 74.81), (145.4, 73.27), (145.39, 5.74), (145.12, 4.2), (144.46, 2.78), (143.64, 1.76), (142.4, 0.8), (140.95, 0.2), (139.4, 0.0)]
# El mecanismo se apoya en los "patines" de los pivotes de los párpados: la base queda en el aire
ALTURA_BASE = 8.0            # del apoyo a la cara de abajo de la base
OJO_ALTURA = 27.2            # centro de los ojos sobre el apoyo
OJO_ADELANTE = 21.0          # centro de los ojos por delante del borde de la base
DIAMETRO_OJO = 32.0
RADIO_PARPADOS = 19.5
SEPARACION_OJOS = 75.0
ALTO_MECANISMO = 63.5        # del punto más bajo de las piezas al arco central (fijo): medido, 2,5"
X_PATINES = (6.0, 21.0)      # en bx, a cada lado (simétricos), con las palancas de los párpados: foto de abajo
BY_PATINES = (-15.0, 62.0)
X_ANILLO = (9.5, 15.1)       # anillo del pivote del párpado (en bx), al centro de los ojos   # abajo; el anillo de adelante va aparte, a la altura de los ojos

# ---------------- Dónde va ------------------------------------------------------------------
GROSOR_BANDEJA = 5.0         # lo justo para las ranuras de cola de milano de abajo
MARGEN = 3.0                 # entre la base y la pared de la carcasa
PARED = 2.4
HOLGURA = 0.3

RADIO_ESQUINAS = 12.0        # de la cuna de la base

# ---------------- Electrónica atrás de la base: Arduino UNO y PCA9685, lado a lado -----------
# Las dos placas van a lo largo (hacia atrás). El USB y el jack de la UNO salen por la pared de atrás.
SEPARADOR = 5.0                  # altura de los postes sobre la bandeja
Y_BAHIA = None                   # frente de la zona de las placas: se calcula abajo (justo detrás de la cuna)
UNO_PLACA = (68.6, 53.4)         # largo x ancho
# Agujeros de la UNO medidos desde la esquina del lado del jack, en (largo, ancho)
UNO_AGUJEROS = [(13.97, 2.54), (15.24, 50.8), (66.04, 7.62), (66.04, 35.56)]
UNO_USB = (38.1, 12.0, 10.9, 6.2)    # centro (en el ancho), ancho, alto y cuánto sobresale
UNO_JACK = (7.6, 9.0, 11.0)          # centro (en el ancho), ancho, alto
UNO_X = -65.0                    # canto izquierdo de la UNO (vista de arriba, frente adelante)
UNO_ALTO = 15.0                  # componentes sobre la placa
PCA_PLACA = (62.5, 25.4)         # largo x ancho
PCA_AGUJEROS = (55.9, 19.0)      # entre centros (M2.5)
PCA_ALTO = 18.0                  # con los pines de los servos y la bornera
PCA_X = 30.0                     # centro de la PCA9685
ATRAS = 76.0                     # cuánto se alarga la bandeja hacia atrás para las placas

# ---------------- Montura: ganchos adelante y brazo pivotante atrás ---------------------------
# La pantalla tiene su cara de adelante en y=0 y su borde de arriba en z=Z_PANTALLA.
COLA = (8.0, 11.0, 3.0)      # cola de milano: ancho en la cara de abajo, ancho adentro, alto (deja 2 mm arriba)
HOLGURA_COLA = 0.2           # por lado: entra a presión
GANCHO_X = 45.0              # centro de cada gancho (|x|): deja 66 mm libres al centro para la cámara
GANCHO_ANCHO = 24.0
GANCHO_PLACA = 3.0           # lo que queda entre la bandeja y el borde de la pantalla
GANCHO_PESTANA = (2.5, 8.0)  # grosor y cuánto baja por delante de la pantalla
GANCHO_LARGO = 30.0          # lo que entra en la ranura
INCLINACION_MAX = 25.0       # la pestaña sirve para pantallas echadas hasta este ángulo
Z_PANTALLA = -GROSOR_BANDEJA - GANCHO_PLACA
Y_PIVOTE = -45.0             # eje del brazo, detrás de la pantalla (aguanta pantallas de hasta ~35 mm)
SOPORTE_PLACA = 3.0
PIVOTE_RADIO = 6.0
PIVOTE_ANCHO = 20.0          # nudillo del brazo (tornillo M3 x 30)
Z_PIVOTE = -GROSOR_BANDEJA - SOPORTE_PLACA - PIVOTE_RADIO
BRAZO_LARGO = 70.0           # del eje al centro del pie
BRAZO_ANCHO = 36.0
BRAZO_GROSOR = 6.0           # parejo: el brazo se imprime acostado
PIE_RADIO = 3.0              # pie redondeado (medio grosor del brazo); lleva fieltro
AGUJERO_M3 = 1.7

# Ojos al ras del frente de la pantalla, vistos de lado
Y_OJOS = -DIAMETRO_OJO / 2
Y_BASE = Y_OJOS - OJO_ADELANTE   # borde de adelante de la base del mecanismo
# Caja de la electrónica (MDF), solo atrás: el mecanismo queda a la vista
CAJA_PARED = 3.0
X_CAJA_IN = BASE_ANCHO / 2 + MARGEN
Y_CAJA_FRENTE_IN = Y_BASE - BASE_FONDO - 3.0 - CAJA_PARED   # justo detrás de la cuna de la base
Y_CAJA_ATRAS_IN = Y_BASE - BASE_FONDO - ATRAS - MARGEN
Y_BANDEJA_FRENTE = -10.0        # la bandeja llega casi al frente de la pantalla, bajo los ojos
Y_BAHIA = Y_CAJA_FRENTE_IN - 1.0
# Ventanas en la bandeja (x0, x1, y0, y1): esquivan los patines, las barras de abajo del
# mecanismo (al centro), la cuna, las ranuras y los postes de las placas
VENTANAS = [(-28, 28, -32, -14),                              # adelante, entre los ganchos
            (19, 48, -118, -54), (-48, -24, -118, -54),         # bajo el mecanismo, a los lados de las barras
            (-11, 6, -80, -58),                                 # entre las barras del centro
            (-12, 8, -126, -84),                                # detrás de las barras
            (-8, 14, -205, -146),                               # entre la UNO y la PCA9685
            (-54, -33, -186, -148), (23.5, 36.5, -192, -149),   # bajo cada placa, entre sus postes
            (47, 70, -205, -143)]                               # al lado de la PCA9685
EROSION = RADIO_ESQUINAS - MARGEN - PARED   # deja la esquina de afuera con RADIO_ESQUINAS
cilindro_x = mm.cilindro_x


def a_mundo(bx, by):
    return (bx - BASE_ANCHO / 2, Y_BASE - by)


def contorno(delante=0.0, crecer=0.0, redondeo=0.0, atras=0.0):
    """Contorno de la base (en el mundo), alargado `delante` mm hacia adelante y agrandado
    `crecer` mm. Con `redondeo` se achica y se vuelve a agrandar esa cantidad, así todas las
    piezas que usan el mismo `redondeo` quedan con esquinas concéntricas."""
    pts = [a_mundo(bx, by) for bx, by in CONTORNO_BASE]
    pts = [(x, y + delante if y >= Y_BASE - 10 else y) for x, y in pts]   # estira la parte de adelante
    if atras:   # atrás: esquinas en ángulo recto (redondeadas), para que quepan las placas
        y_atras = Y_BASE - BASE_FONDO - atras
        nuevos, puesto = [], False
        for x, y in pts:
            if y < Y_BASE - 60:
                if not puesto:
                    lado = 1 if x > 0 else -1
                    nuevos += [(lado * BASE_ANCHO / 2, y_atras), (-lado * BASE_ANCHO / 2, y_atras)]
                    puesto = True
            else:
                nuevos.append((x, y))
        pts = nuevos
    w = cq.Workplane("XY").polyline(pts).close()
    r = max(redondeo, 0.0)
    if r:
        w = w.offset2D(-r, "intersection").offset2D(r + crecer, "arc")
    elif crecer:
        w = w.offset2D(crecer, "arc")
    return w


def prisma(delante, crecer, redondeo, z0, z1, atras=0.0):
    return contorno(delante, crecer, redondeo, atras).extrude(z1 - z0).translate((0, 0, z0))


def caja_exterior(crecer, z0, z1):
    """Contorno de la carcasa y la bandeja: la base, alargada adelante (ojos) y atrás (placa)."""
    return prisma(DELANTE, crecer, EROSION, z0, z1, ATRAS)


Y_USB = Y_BAHIA - UNO_PLACA[0]          # canto de atrás de la UNO (el del USB)
Y_PCA = Y_BAHIA - PCA_PLACA[0] / 2       # centro de la PCA9685


def x_uno(a):
    """x en el mundo de un punto de la UNO a `a` mm de su canto de abajo (vista de arriba con el USB
    a la izquierda). Con el USB hacia atrás, ese canto queda a la derecha (x mayor)."""
    return UNO_X + UNO_PLACA[1] - a


def postes():
    """Centros de los postes de las dos placas."""
    uno = [(x_uno(a), Y_USB + l) for l, a in UNO_AGUJEROS]
    pca = [(PCA_X + sx * PCA_AGUJEROS[1] / 2, Y_PCA + sy * PCA_AGUJEROS[0] / 2)
           for sx in (-1, 1) for sy in (-1, 1)]
    return uno + pca


DELANTE = 0.0


def rect_(x, y0, y1, z0, z1):
    return cq.Workplane("XY").box(2 * x, y1 - y0, z1 - z0).translate((0, (y0 + y1) / 2, (z0 + z1) / 2))


def bandeja():
    """Placa recta con: la cuna que sujeta la base del mecanismo por los lados y por atrás (con un
    apoyo a ALTURA_BASE), los postes de la UNO y la PCA9685, el reborde donde encaja la caja de la
    electrónica (atrás) y, por debajo, las ranuras de cola de milano de los ganchos y del brazo."""
    xe = X_CAJA_IN + CAJA_PARED
    solido = rect_(xe, Y_CAJA_ATRAS_IN - CAJA_PARED, Y_BANDEJA_FRENTE, -GROSOR_BANDEJA, 0).edges("|Z").fillet(1.0)
    # Reborde de la caja: a los lados y atrás (adelante quedan las placas)
    h = HOLGURA
    reborde = rect_(X_CAJA_IN - h, Y_CAJA_ATRAS_IN + h, Y_CAJA_FRENTE_IN - h, 0, 6).cut(
        rect_(X_CAJA_IN - h - 2, Y_CAJA_ATRAS_IN + h + 2, Y_CAJA_FRENTE_IN + 10, -1, 7))
    solido = solido.union(reborde)
    # Cuna: pared alrededor del canto de la base y repisa donde apoya, solo a los lados y atrás
    alto_cuna = ALTURA_BASE + BASE_GROSOR
    cuna = prisma(0, 2.5, EROSION, 0, alto_cuna).cut(prisma(0, 0.5, 0, ALTURA_BASE, alto_cuna + 1))
    cuna = cuna.cut(prisma(0, -3.0, 0, -1, alto_cuna + 1))
    # Fuera la parte de adelante, donde están los patines y los ojos
    cuna = cuna.cut(cq.Workplane("XY").box(300, 200, 100).translate((0, Y_BASE - 45 + 100, 0)))
    solido = solido.union(cuna)
    # Postes para la UNO y la PCA9685 (tornillos M2.5 x 6 autorroscantes, agujero de 2.2)
    for c in postes():
        poste = cq.Workplane("XY").circle(2.8).extrude(SEPARADOR).translate((c[0], c[1], 0))
        solido = solido.union(poste).cut(
            cq.Workplane("XY").circle(1.1).extrude(SEPARADOR + 1).translate((c[0], c[1], 0.5)))
    # Ventanas para aliviar la impresión, donde no apoya nada
    for x0, x1, y0, y1 in VENTANAS:
        solido = solido.cut(rect_((x1 - x0) / 2, y0, y1, -GROSOR_BANDEJA - 1, 0.01)
                            .edges("|Z").fillet(min(4.0, (x1 - x0) / 2 - 0.1, (y1 - y0) / 2 - 0.1))
                            .translate(((x0 + x1) / 2, 0, 0)))
    # Ranuras de cola de milano abajo: dos para los ganchos (abiertas adelante) y una para el
    # soporte del brazo (abierta al lado derecho)
    for sx in (-1, 1):
        solido = solido.cut(cola_y(sx * GANCHO_X, Y_BANDEJA_FRENTE - GANCHO_LARGO - 0.5, Y_BANDEJA_FRENTE + 1, 0.0))
    solido = solido.cut(cola_x(Y_PIVOTE, -PIVOTE_ANCHO / 2 - 6.6, 200, 0.0))
    return solido


def trapecio(ancho_abajo, ancho_arriba, alto):
    """Sección de la cola de milano (angosta abajo), en coordenadas (a lo ancho, z) desde la cara de abajo."""
    return [(-ancho_abajo / 2, 0), (ancho_abajo / 2, 0), (ancho_arriba / 2, alto), (-ancho_arriba / 2, alto)]


def _prisma_seccion(pts, largo, eje):
    """Extruye la sección `pts` (u, z) a lo largo de `eje` ('x' o 'y'), desde 0 hasta `largo`."""
    if eje == "y":
        w = cq.Workplane("XZ").polyline(pts).close().extrude(-largo)     # XZ mira hacia -y
    else:
        w = cq.Workplane("YZ").polyline(pts).close().extrude(largo)
    return w


def cola_y(x, y0, y1, holgura):
    """Cola de milano a lo largo de y (ranura si holgura=0; lengüeta si holgura>0), con la cara
    angosta en la cara de abajo de la bandeja."""
    a, b_, h = COLA
    pts = trapecio(a - 2 * holgura, b_ - 2 * holgura, h - holgura)
    return _prisma_seccion(pts, y1 - y0, "y").translate((x, y0, -GROSOR_BANDEJA))


def cola_x(y, x0, x1, holgura):
    a, b_, h = COLA
    pts = trapecio(a - 2 * holgura, b_ - 2 * holgura, h - holgura)
    return _prisma_seccion(pts, x1 - x0, "x").translate((x0, y, -GROSOR_BANDEJA))


def y_frente_bandeja():
    return Y_BANDEJA_FRENTE


def gancho(sx=1, y_frente=None):
    """Gancho del lado `sx`: placa que pasa sobre el borde de la pantalla, pestaña que baja por
    delante y lengüeta de cola de milano que entra en la bandeja desde adelante."""
    yf = y_frente_bandeja() if y_frente is None else y_frente
    x = sx * GANCHO_X
    w = GANCHO_ANCHO
    p_gr, p_alto = GANCHO_PESTANA
    placa = caja(x - w / 2, x + w / 2, yf - GANCHO_LARGO, p_gr, Z_PANTALLA, -GROSOR_BANDEJA)
    # La cara de adentro de la pestaña va inclinada para pantallas echadas de 0° a INCLINACION_MAX
    avance = p_alto * math.tan(math.radians(INCLINACION_MAX))
    perfil = [(0.0, Z_PANTALLA + 0.01), (p_gr, Z_PANTALLA + 0.01), (avance + p_gr, Z_PANTALLA - p_alto),
              (avance + 0.2, Z_PANTALLA - p_alto)]
    pestana = (cq.Workplane("YZ").polyline(perfil).close().extrude(w).translate((x - w / 2, 0, 0)))
    g = placa.union(pestana)
    lengueta = cola_y(x, yf - GANCHO_LARGO + 0.3, yf, HOLGURA_COLA)
    return g.union(lengueta)


def soporte_brazo():
    """Soporte del brazo: lengüeta de cola de milano (entra desde el lado derecho) y dos orejas
    con el eje del brazo."""
    ancho = PIVOTE_ANCHO + 2 * 6.4
    placa = caja(-ancho / 2, ancho / 2, Y_PIVOTE - 10, Y_PIVOTE + 10, -GROSOR_BANDEJA - SOPORTE_PLACA, -GROSOR_BANDEJA)
    sol = placa.union(cola_x(Y_PIVOTE, -ancho / 2, ancho / 2, HOLGURA_COLA))
    for sx in (-1, 1):
        x0, x1 = sx * (PIVOTE_ANCHO / 2 + 0.4), sx * (PIVOTE_ANCHO / 2 + 6.4)
        oreja = (caja(min(x0, x1), max(x0, x1), Y_PIVOTE - PIVOTE_RADIO, Y_PIVOTE + PIVOTE_RADIO,
                      Z_PIVOTE, -GROSOR_BANDEJA - SOPORTE_PLACA)
                 .union(cilindro_x(PIVOTE_RADIO, min(x0, x1), max(x0, x1), Y_PIVOTE, Z_PIVOTE)))
        sol = sol.union(oreja)
    return sol.cut(cilindro_x(AGUJERO_M3, -100, 100, Y_PIVOTE, Z_PIVOTE))


def brazo_local():
    """Brazo con el eje en el origen, colgando hacia -z."""
    nudillo = cilindro_x(PIVOTE_RADIO, -PIVOTE_ANCHO / 2 + 0.3, PIVOTE_ANCHO / 2 - 0.3, 0, 0)
    cuello = caja(-PIVOTE_ANCHO / 2 + 0.3, PIVOTE_ANCHO / 2 - 0.3, -BRAZO_GROSOR / 2, BRAZO_GROSOR / 2,
                  -PIVOTE_RADIO - 6, 0)
    barra = caja(-BRAZO_ANCHO / 2, BRAZO_ANCHO / 2, -BRAZO_GROSOR / 2, BRAZO_GROSOR / 2,
                 -BRAZO_LARGO, -PIVOTE_RADIO - 4).edges("|Y").fillet(5)
    pie = cilindro_x(PIE_RADIO, -BRAZO_ANCHO / 2 + 3, BRAZO_ANCHO / 2 - 3, 0, -BRAZO_LARGO)
    brazo_ = nudillo.union(cuello).union(barra).union(pie)
    # Todo del mismo grosor (el nudillo queda plano a los lados): se imprime acostado, sin soportes
    brazo_ = brazo_.intersect(caja(-100, 100, -BRAZO_GROSOR / 2, BRAZO_GROSOR / 2, -200, 50))
    return brazo_.cut(cilindro_x(AGUJERO_M3, -100, 100, 0, 0))


def angulo_brazo(grosor, inclinacion):
    """Ángulo del brazo (grados hacia adelante desde la vertical) para que el pie toque la parte
    de atrás de una pantalla de `grosor` mm echada `inclinacion` grados."""
    t = math.radians(inclinacion)
    d = (math.sin(t), -math.cos(t))                 # bajando por la pantalla
    n = (-math.cos(t), -math.sin(t))                # hacia atrás de la cara de atrás
    q = (-grosor * math.cos(t) + PIE_RADIO * n[0], Z_PANTALLA - grosor * math.sin(t) + PIE_RADIO * n[1])
    w = (q[0] - Y_PIVOTE, q[1] - Z_PIVOTE)
    bb = d[0] * w[0] + d[1] * w[1]
    cc = w[0] ** 2 + w[1] ** 2 - BRAZO_LARGO ** 2
    s_ = -bb + math.sqrt(max(bb * bb - cc, 0))
    f = (q[0] + s_ * d[0], q[1] + s_ * d[1])
    return math.degrees(math.atan2(f[0] - Y_PIVOTE, -(f[1] - Z_PIVOTE)))


def brazo(grosor=None, inclinacion=None):
    b_ = brazo_local()
    if grosor is not None:
        b_ = b_.rotate((0, 0, 0), (1, 0, 0), angulo_brazo(grosor, inclinacion))
    return b_.translate((0, Y_PIVOTE, Z_PIVOTE))


def pantalla(grosor, inclinacion, alto=200.0):
    """Pantalla de ejemplo: cara de adelante en y=0 arriba, echada hacia atrás `inclinacion` grados."""
    p = cq.Workplane("XY").box(304.0, grosor, alto).translate((0, -grosor / 2, -alto / 2))
    return p.rotate((0, 0, 0), (1, 0, 0), inclinacion).translate((0, 0, Z_PANTALLA))


def camara(inclinacion):
    c = cq.Workplane("XY").sphere(0.5).translate((0, 0.5, -mm.CAMARA_BAJO_BORDE))
    return c.rotate((0, 0, 0), (1, 0, 0), inclinacion).translate((0, 0, Z_PANTALLA)).val().Center()


def caja(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0).translate(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))


def mecanismo():
    """Versión simplificada del EyeMech armado, para revisar choques y dibujar."""
    base = contorno().extrude(BASE_GROSOR).translate((0, 0, ALTURA_BASE))
    servos = caja(-55, 55, Y_BASE - 80, Y_BASE - 15, ALTURA_BASE + BASE_GROSOR, 42)
    arco = caja(-45, 45, Y_BASE - 40, Y_OJOS - 8, OJO_ALTURA + 14, ALTO_MECANISMO)
    piezas = {"base del mecanismo": base, "servos": servos, "arco": arco}
    ojos = parpados = patines = None
    for sx in (-1, 1):
        c = (sx * SEPARACION_OJOS / 2, Y_OJOS, OJO_ALTURA)
        o = cq.Workplane("XY").sphere(DIAMETRO_OJO / 2).translate(c)
        p = cq.Workplane("XY").sphere(RADIO_PARPADOS).translate(c)
        x0, x1 = (X_PATINES if sx < 0 else (BASE_ANCHO - X_PATINES[1], BASE_ANCHO - X_PATINES[0]))
        (xa, _), (xb, _) = a_mundo(x0, 0), a_mundo(x1, 0)
        pat = caja(xa, xb, Y_BASE - BY_PATINES[1], Y_BASE - BY_PATINES[0], 0.2, ALTURA_BASE).union(
            cilindro_x(6, sx * (BASE_ANCHO / 2 - X_ANILLO[1]), sx * (BASE_ANCHO / 2 - X_ANILLO[0]), Y_OJOS, OJO_ALTURA))
        ojos = o if ojos is None else ojos.union(o)
        parpados = p if parpados is None else parpados.union(p)
        patines = pat if patines is None else patines.union(pat)
    piezas["PCA9685"] = caja(PCA_X - PCA_PLACA[1] / 2, PCA_X + PCA_PLACA[1] / 2, Y_PCA - PCA_PLACA[0] / 2,
                             Y_PCA + PCA_PLACA[0] / 2, SEPARADOR + 0.1, SEPARADOR + PCA_ALTO)
    z_placa = SEPARADOR + 1.6
    uno = caja(UNO_X, UNO_X + UNO_PLACA[1], Y_USB, Y_BAHIA, SEPARADOR + 0.1, z_placa + UNO_ALTO - 4)
    for centro, ancho_, alto_, sale in (UNO_USB, UNO_JACK + (2.0,)):
        uno = uno.union(caja(x_uno(centro) - ancho_ / 2, x_uno(centro) + ancho_ / 2, Y_USB - sale,
                             Y_USB + 15, z_placa, z_placa + alto_))
    piezas["Arduino UNO"] = uno
    piezas.update({"ojos": ojos, "párpados": parpados, "pivotes de los párpados": patines})
    return piezas


def piezas():
    return {"bandeja": bandeja(), "gancho": gancho(1),
            "soporte_brazo": soporte_brazo(), "brazo": brazo()}


def armado(ejemplo, bandeja_=None):
    grosor, inclinacion = mm.EJEMPLOS[ejemplo]
    todas = {"bandeja": bandeja_ if bandeja_ is not None else bandeja(),
             "gancho izquierdo": gancho(-1), "gancho derecho": gancho(1),
             "soporte del brazo": soporte_brazo(), "brazo": brazo(grosor, inclinacion)}
    return todas, pantalla(grosor, inclinacion)


def revisar(bandeja_=None, cubierta_=None):
    meca = mecanismo()
    for ejemplo, (grosor, inclinacion) in mm.EJEMPLOS.items():
        todas, pant = armado(ejemplo, bandeja_)
        if cubierta_ is not None:
            todas["caja"] = cubierta_
        print(f"\n{ejemplo}: pantalla de {grosor} mm echada {inclinacion}° atrás; "
              f"brazo a {angulo_brazo(grosor, inclinacion):.0f}° de la vertical")
        hubo = False
        nombres = list(todas)
        for nc, cosa in dict(meca, pantalla=pant).items():
            for np_ in nombres:
                try:
                    v = cosa.intersect(todas[np_]).val().Volume()
                except Exception:
                    v = 0
                if v > 1:
                    hubo = True
                    print(f"  choque: {nc} con {np_}: {v:.0f} mm³")
        for i in range(len(nombres)):
            for j in range(i + 1, len(nombres)):
                try:
                    v = todas[nombres[i]].intersect(todas[nombres[j]]).val().Volume()
                except Exception:
                    v = 0
                if v > 1:
                    hubo = True
                    print(f"  choque: {nombres[i]} con {nombres[j]}: {v:.0f} mm³")
        print("  sin choques" if not hubo else "")
        cam = camara(inclinacion)
        ojo_abajo = (Y_OJOS, OJO_ALTURA - DIAMETRO_OJO / 2)
        print(f"  ojos: la punta queda a {Y_OJOS + DIAMETRO_OJO / 2:.1f} mm del frente de la pantalla; "
              f"lo más bajo de los ojos, {ojo_abajo[1] - cam.z:.0f} mm sobre la cámara y "
              f"{cam.y - ojo_abajo[0]:.0f} mm detrás de ella (fuera de su vista)")


if __name__ == "__main__":
    salida = Path(__file__).parent / "stl_bandeja"
    salida.mkdir(exist_ok=True)
    for nombre, pieza in piezas().items():
        cq.exporters.export(pieza, str(salida / f"{nombre}.stl"), tolerance=0.05, angularTolerance=0.1)
        caja_ = pieza.val().BoundingBox()
        print(f"{nombre:9s} {caja_.xlen:6.1f} x {caja_.ylen:6.1f} x {caja_.zlen:6.1f} mm")
    if "--revisar" in sys.argv:
        revisar()
