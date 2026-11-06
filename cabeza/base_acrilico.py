# Base de acrílico de 5 mm cortada en láser (base_acrilico5_CORTADA.svg, ya cortada: sus 20
# ranuras no se cambian) y piezas chicas impresas en 3D que se encajan en esas ranuras. Cada
# pieza tiene una cara plana para la cama y no necesita soportes:
#   gancho.stl (x2)       perfil parejo de 8 mm (con su clip): se imprime acostado de lado
#   pata_trasera.stl      placa + diagonal que se apoya atrás de la pantalla; perfil parejo de 8 mm,
#                         se imprime acostada de lado; se encaja con 2 clips, como los ganchos
#   cuna_izquierda/derecha/atras.stl  paradas; se fijan con M3 x 12 desde abajo, por un tapón
#   soporte_uno.stl, soporte_pca.stl  planas, postes arriba; se fijan con M3 x 10 desde abajo
#   tapon.stl (x10)       entra desde abajo en cada ranura chica, centra el tornillo y hace de golilla
#   (cuna y soportes de las placas)
# La caja de la electrónica (caja_electronica.py) entra con dientes en las ranuras de atrás.
#
# Uso:  .venv-cad/bin/python cabeza/base_acrilico.py [--revisar]
# Mismos ejes que bandeja.py: z=0 es la cara de arriba del acrílico; y=0 el frente de la pantalla.
import math
import sys
from pathlib import Path
import cadquery as cq
from shapely.geometry import box as srect
from shapely.ops import unary_union
from shapely import affinity

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI))
import bandeja as b
import caja_electronica as ce

ACRILICO = b.GROSOR_BANDEJA      # 5 mm
KERF = 0.15
HOLGURA_CLIP = 0.15
# Pinza fija en U con ángulo: los ganchos y la pata siguen la inclinación de la pantalla, así la
# base queda horizontal y el peso no le hace palanca a la tapa
INCLINACION_PANTALLA = 15.0      # grados que se echa la pantalla hacia atrás en uso normal
GROSOR_PANTALLA = 4.5            # borde de arriba de la tapa del MacBook Air
HOLGURA_PANTALLA = 1.0           # para un fieltro o goma en la pata
PATA_LARGO = 60.0                # cuánto baja la pata por detrás de la pantalla
PATA_GROSOR = 6.0
REFUERZO = 18.0                  # (ya no se usa: ahora la pata es un triángulo completo)
MARCO = 7.0                      # grosor de la diagonal
MARGEN_BASE = 4.0                # la placa sobresale de la caja a los lados y atrás
VENTANAS = False                 # sin ventanas: en el láser solo agregarían tiempo de corte

# Clip: dos patas que pasan por una ranura del acrílico y se enganchan del otro lado
CLIP = dict(ancho=8.0, pata=2.5, separacion=1.5, gancho=0.8, alto_gancho=2.0)
CLIP_CHICO = dict(ancho=8.0, pata=1.8, separacion=1.2, gancho=0.6, alto_gancho=1.8)

X_PLACA = ce.W / 2 + MARGEN_BASE
Y_PLACA = (ce.Y_FRENTE - ce.D - MARGEN_BASE, b.Y_BANDEJA_FRENTE)


def clip(x, y, z0, sentido, eje, c=CLIP):
    """Clip con las patas saliendo de z0 hacia arriba (sentido=+1) o hacia abajo (-1), a lo largo
    de todo el grosor del acrílico. `eje` = dirección del ancho de las patas ('x' o 'y')."""
    g, p, gb, hb = c["separacion"] / 2, c["pata"], c["gancho"], c["alto_gancho"]
    largo = ACRILICO + 0.2
    patas = None
    for s in (1, -1):
        pts = [(g, 0), (g + p, 0), (g + p, largo), (g + p + gb, largo), (g + p * 0.4, largo + hb), (g, largo + hb)]
        pts = [(s * t, sentido * h) for t, h in pts]
        if eje == "x":
            w = cq.Workplane("YZ").polyline(pts).close().extrude(c["ancho"]).translate((x - c["ancho"] / 2, y, z0))
        else:
            w = cq.Workplane("XZ").polyline(pts).close().extrude(-c["ancho"]).translate((x, y - c["ancho"] / 2, z0))
        patas = w if patas is None else patas.union(w)
    return patas


def ranura_clip(x, y, eje, c=CLIP):
    grosor = 2 * (c["separacion"] / 2 + c["pata"]) + 2 * HOLGURA_CLIP
    largo = c["ancho"] + 2 * HOLGURA_CLIP
    return (x, y, largo, grosor) if eje == "x" else (x, y, grosor, largo)


def caja(x0, x1, y0, y1, z0, z1):
    return b.caja(x0, x1, y0, y1, z0, z1)


# ---------------- Piezas impresas, en su lugar --------------------------------------------------
CLIPS_GANCHO = [(-20.0, "x"), (-34.0, "x")]       # (y, eje) de cada clip de un gancho


def gancho(sx=1):
    x, w = sx * b.GANCHO_X, CLIP["ancho"]      # mismo ancho que el clip: todo el gancho es un perfil parejo
    p_gr, p_alto = b.GANCHO_PESTANA
    y_atras = min(y for y, _ in CLIPS_GANCHO) - (CLIP["separacion"] / 2 + CLIP["pata"]) - 0.5   # termina en el clip
    placa = caja(x - w / 2, x + w / 2, y_atras, p_gr + 0.3 + 0.6, b.Z_PANTALLA, -ACRILICO)
    # Pestaña paralela al frente de la pantalla echada INCLINACION_PANTALLA grados
    zp, p_alto = b.Z_PANTALLA, 10.0
    d, nf = direcciones()
    a = (0.3 * nf[0], zp + 0.3 * nf[1])
    b_ = (a[0] + p_alto * d[0], a[1] + p_alto * d[1])
    perfil = [(a[0], zp + 0.01), b_, (b_[0] + p_gr * nf[0], b_[1] + p_gr * nf[1]),
              (a[0] + p_gr * nf[0], zp + 0.01)]
    g = placa.union(cq.Workplane("YZ").polyline(perfil).close().extrude(w).translate((x - w / 2, 0, 0)))
    for y, eje in CLIPS_GANCHO:
        g = g.union(clip(x, y, -ACRILICO, 1, eje))
    return g


CLIPS_SOPORTE = [(-2.0, b.Y_PIVOTE - 6), (-2.0, b.Y_PIVOTE + 6)]


def espiga(x, y, eje, c=CLIP, agujero=3.4):
    """Espiga recta que entra justa en la ranura de un clip, al ras con la cara de arriba del
    acrílico, con un agujero para un tornillo que la aprieta desde arriba (con golilla)."""
    _, _, ax, ay = ranura_clip(x, y, eje, c)
    e = caja(x - ax / 2 + 0.15, x + ax / 2 - 0.15, y - ay / 2 + 0.15, y + ay / 2 - 0.15, -ACRILICO, -0.2)
    return e.cut(cq.Workplane("XY").circle(agujero / 2).extrude(30).translate((x, y, -25)))


def direcciones():
    """d: bajando por la pantalla echada; nf: normal hacia adelante (perfil y, z)."""
    t = math.radians(INCLINACION_PANTALLA)
    return (math.sin(t), -math.cos(t)), (math.cos(t), math.sin(t))


def pata_trasera():
    """Pinza fija de atrás: placa bajo el acrílico (en las ranuras del antiguo soporte del brazo),
    pata paralela a la parte de atrás de la pantalla echada y refuerzo triangular. Es un perfil
    parejo de 8 mm: se imprime acostada de lado, sin soportes, con las capas en el plano de la carga."""
    x, w = CLIPS_SOPORTE[0][0], CLIP["ancho"]
    zp, za = b.Z_PANTALLA, -ACRILICO
    d, nf = direcciones()
    nb = (-nf[0], -nf[1])                                      # hacia atrás
    g = GROSOR_PANTALLA + HOLGURA_PANTALLA
    base = (g * nb[0], zp + g * nb[1])                         # cara de la pata que mira a la pantalla, arriba

    def en_z(p0, z):                                           # punto de la recta p0 + s d a la altura z
        s_ = (z - p0[1]) / d[1]
        return (p0[0] + s_ * d[0], z)
    p1 = en_z(base, zp)
    p2 = (p1[0] + PATA_LARGO * d[0], p1[1] + PATA_LARGO * d[1])
    p3 = (p2[0] + PATA_GROSOR * nb[0], p2[1] + PATA_GROSOR * nb[1])
    atras = (p1[0] + PATA_GROSOR * nb[0], p1[1] + PATA_GROSOR * nb[1])
    p1b = en_z(atras, zp)
    g1 = en_z(atras, zp - REFUERZO)
    g2 = (p1b[0] - REFUERZO, zp)
    # Solo la diagonal y la placa (sin el lado pegado a la pantalla): la diagonal va desde el
    # extremo de atrás de la placa hasta apoyar su punta redondeada atrás de la pantalla
    from shapely.geometry import Polygon, LineString, Point
    y_placa = min(y for _, y in CLIPS_SOPORTE) - (CLIP["separacion"] / 2 + CLIP["pata"]) - 0.5   # termina en el clip
    placa = Polygon([(y_placa, za), (p1[0], za), (p1[0], zp), (y_placa, zp)])
    pie = (p2[0] + MARCO / 2 * nb[0], p2[1] + MARCO / 2 * nb[1])          # centro de la punta
    raiz = (y_placa + MARCO / 2, zp)
    diagonal = LineString([raiz, pie]).buffer(MARCO / 2, 16)
    union_ = Polygon([(y_placa, zp), (y_placa + 3 * MARCO, zp), (y_placa, zp - 2 * MARCO)])   # cartela
    perfil = placa.union(diagonal).union(union_).union(Point(pie).buffer(MARCO / 2 + 0.5, 16))
    perfil = perfil.intersection(Polygon([(-500, za), (500, za), (500, -500), (-500, -500)]))
    sol = cq.Workplane("YZ").polyline(list(perfil.exterior.coords)[:-1]).close().extrude(w)
    sol = sol.translate((x - w / 2, 0, 0))
    for xx, y in CLIPS_SOPORTE:   # mismos clips que los ganchos: se encaja a presión, sin tornillos
        sol = sol.union(clip(xx, y, -ACRILICO, 1, "x"))
    return sol


def cuna():
    """La cuna de la bandeja impresa (pared y repisa alrededor de la base), en tres partes."""
    alto = b.ALTURA_BASE + b.BASE_GROSOR
    c = b.prisma(0, 2.5, b.EROSION, 0, alto).cut(b.prisma(0, 0.5, 0, b.ALTURA_BASE, alto + 1))
    c = c.cut(b.prisma(0, -3.0, 0, -1, alto + 1))
    c = c.cut(cq.Workplane("XY").box(300, 200, 100).translate((0, b.Y_BASE - 45 + 100, 0)))
    x_lado = b.BASE_ANCHO / 2 - 0.25
    y_atras = b.Y_BASE - b.BASE_FONDO - 0.25
    partes = {
        "cuna_izquierda": (c.intersect(caja(-200, -30, -400, 100, -1, 100)), [(-x_lado, b.Y_BASE - 52, "y"), (-x_lado, b.Y_BASE - 70, "y")]),
        "cuna_derecha": (c.intersect(caja(30, 200, -400, 100, -1, 100)), [(x_lado, b.Y_BASE - 52, "y"), (x_lado, b.Y_BASE - 70, "y")]),
        "cuna_atras": (c.intersect(caja(-30, 30, -400, 100, -1, 100)), [(-15, y_atras, "x"), (15, y_atras, "x")]),
    }
    out = {}
    for n, (sol, clips) in partes.items():
        for x, y, eje in clips:
            sol = sol.cut(cq.Workplane("XY").circle(1.4).extrude(8).translate((x, y, -0.1)))
        out[n] = (sol, clips)
    return out


def _soporte_placa(postes, clips):
    """Barras de 2 mm que unen los postes de una placa, con clips hacia abajo."""
    sol = None
    n = len(postes)
    cx_, cy_ = sum(p[0] for p in postes) / len(postes), sum(p[1] for p in postes) / len(postes)
    anillo = sorted(postes, key=lambda p: math.atan2(p[1] - cy_, p[0] - cx_))   # contorno sin cruces
    for i in range(4):
        p0, p1 = anillo[i], anillo[(i + 1) % 4]
        from shapely.geometry import LineString
        pol = LineString([p0, p1]).buffer(3.0, 8)
        barra = cq.Workplane("XY").polyline(list(pol.exterior.coords)[:-1]).close().extrude(2.0)
        sol = barra if sol is None else sol.union(barra)
    for x, y in postes:
        sol = sol.union(cq.Workplane("XY").circle(3.3).extrude(b.SEPARADOR).translate((x, y, 0)))
    for x, y in postes:
        sol = sol.cut(cq.Workplane("XY").circle(1.4).extrude(b.SEPARADOR + 1).translate((x, y, 0.5)))
    for x, y in clips:
        cerca = min(postes, key=lambda q: (q[0] - x) ** 2 + (q[1] - y) ** 2)   # une el tetón al poste más cercano
        pol = LineString([(x, y), cerca]).buffer(3.0, 8)
        sol = sol.union(cq.Workplane("XY").polyline(list(pol.exterior.coords)[:-1]).close().extrude(2.0))
        # Tetón del tornillo de abajo. Si queda pegado a un poste (bajo el ICSP de la UNO) se deja
        # al ras de las barras, 2 mm, para no tocar los pines de la placa: ahí va un M3 x 8.
        junto = math.dist((x, y), cerca) < 8
        alto = 2.0 if junto else 4.0
        sol = sol.union(cq.Workplane("XY").circle(3.3).extrude(alto).translate((x, y, 0)))
        sol = sol.cut(cq.Workplane("XY").circle(1.4).extrude(alto - 0.2 if not junto else alto + 1).translate((x, y, -0.1)))
    return sol


def postes_uno():
    return b.postes()[:4]


def postes_pca():
    return b.postes()[4:]


CLIPS_UNO_CORTADOS = [(-43.41, -141.56), (-38.33, -192.995)]   # ranuras ya cortadas en el acrílico


def clips_uno():
    return CLIPS_UNO_CORTADOS


def clips_pca():
    return [(b.PCA_X, max(q[1] for q in postes_pca())), (b.PCA_X, min(q[1] for q in postes_pca()))]


def tapon(c=CLIP_CHICO):
    """Tapón para una ranura chica: entra desde abajo, llena la ranura y centra el tornillo; su
    pestaña hace de golilla. Se imprime con la pestaña sobre la cama."""
    _, _, ax, ay = ranura_clip(0, 0, "x", c)
    largo, ancho = ax - 0.3, ay - 0.3
    pestana = caja(-largo / 2 - 1.5, largo / 2 + 1.5, -ancho / 2 - 1.5, ancho / 2 + 1.5, 0, 1.5)
    cuerpo = caja(-largo / 2, largo / 2, -ancho / 2, ancho / 2, 1.5, 1.5 + ACRILICO - 0.2)
    return pestana.union(cuerpo).cut(cq.Workplane("XY").circle(1.7).extrude(20).translate((0, 0, -1)))


def piezas_impresas():
    out = {"gancho izquierdo": gancho(-1), "gancho derecho": gancho(1), "pata trasera": pata_trasera()}
    for n, (sol, _) in cuna().items():
        out[n] = sol
    out["soporte_uno"] = _soporte_placa(postes_uno(), clips_uno())
    out["soporte_pca"] = _soporte_placa(postes_pca(), clips_pca())
    return out


# ---------------- Placa de acrílico -------------------------------------------------------------
def ranuras():
    r = []
    for sx in (-1, 1):
        for y, eje in CLIPS_GANCHO:
            r.append(ranura_clip(sx * b.GANCHO_X, y, eje))
    for x, y in CLIPS_SOPORTE:
        r.append(ranura_clip(x, y, "x"))
    for _, (_, clips) in cuna().items():
        for x, y, eje in clips:
            r.append(ranura_clip(x, y, eje, CLIP_CHICO))
    for x, y in clips_uno() + clips_pca():
        r.append(ranura_clip(x, y, "x", CLIP_CHICO))
    r += ce.ranuras_base()
    return r


def placa_2d():
    y0, y1 = Y_PLACA
    p = srect(-X_PLACA + 3, y0 + 3, X_PLACA - 3, y1 - 3).buffer(3, 16)
    huecos = []
    for x0, x1, ya, yb in (b.VENTANAS if VENTANAS else []):
        r = min(4.0, (x1 - x0) / 2 - 0.1, (yb - ya) / 2 - 0.1)
        huecos.append(srect(x0 + r, ya + r, x1 - r, yb - r).buffer(r, 16))
    for x, y, ax, ay in ranuras():
        huecos.append(srect(x - ax / 2, y - ay / 2, x + ax / 2, y + ay / 2))
    return p.difference(unary_union(huecos))


def placa_3d(poly=None):
    poly = poly or placa_2d()
    w = cq.Workplane("XY").polyline(list(poly.exterior.coords)[:-1]).close().extrude(ACRILICO)
    for h in poly.interiors:
        w = w.cut(cq.Workplane("XY").polyline(list(h.coords)[:-1]).close().extrude(ACRILICO + 2).translate((0, 0, -1)))
    return w.translate((0, 0, -ACRILICO))


def svg(archivo):
    poly = affinity.translate(placa_2d().buffer(KERF / 2, join_style=2), X_PLACA + 3, -Y_PLACA[0] + 3)
    ancho, alto = 2 * X_PLACA + 6, Y_PLACA[1] - Y_PLACA[0] + 6
    trazos = []
    for anillo in [poly.exterior] + list(poly.interiors):
        d = "M " + " L ".join(f"{x:.3f},{alto - y:.3f}" for x, y in anillo.coords) + " Z"
        trazos.append(f'<path d="{d}"/>')
    archivo.write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{ancho:.2f}mm" height="{alto:.2f}mm" viewBox="0 0 {ancho:.2f} {alto:.2f}">
<g id="corte" fill="none" stroke="#ff0000" stroke-width="0.1">
{chr(10).join(trazos)}
</g>
<g id="grabado" fill="#0000ff" font-family="Helvetica" font-size="3.5" text-anchor="middle">
<text x="{X_PLACA + 3 - 62:.1f}" y="{alto - (-28.5 - Y_PLACA[0] + 3):.1f}">FRENTE · ARRIBA</text>
</g>
</svg>
''')
    return ancho, alto


def revisar():
    import pantallas as mm
    meca = b.mecanismo()
    placa = placa_3d()
    impresas = piezas_impresas()
    caja_, _ = ce.caja_armada()
    for ejemplo, grosor in (("MacBook Air", GROSOR_PANTALLA),):
        import usbc
        todas = dict(impresas, acrilico=placa, caja=caja_, capsula_usbc=usbc.capsula())
        pant = b.pantalla(grosor, INCLINACION_PANTALLA)
        print(f"\n{ejemplo}: pantalla de {grosor} mm echada {INCLINACION_PANTALLA:.0f}°: la base queda horizontal")
        hubo = False
        nombres = list(todas)
        for nc, cosa in dict(meca, pantalla=pant).items():
            for np_ in nombres:
                try:
                    v = cosa.intersect(todas[np_]).val().Volume()
                except Exception:
                    v = 0
                if v > 1:
                    hubo = True; print(f"  choque: {nc} con {np_}: {v:.0f} mm³")
        for i in range(len(nombres)):
            for j in range(i + 1, len(nombres)):
                try:
                    v = todas[nombres[i]].intersect(todas[nombres[j]]).val().Volume()
                except Exception:
                    v = 0
                if v > 1:
                    hubo = True; print(f"  choque: {nombres[i]} con {nombres[j]}: {v:.0f} mm³")
        print("  sin choques" if not hubo else "")


if __name__ == "__main__":
    carpeta_stl = AQUI / "stl_base"
    carpeta_stl.mkdir(exist_ok=True)
    carpeta_laser = AQUI / "laser"
    aw, ah = svg(carpeta_laser / "base_acrilico5.svg")
    if (carpeta_laser / "base_acrilico5.svg").read_text() != (carpeta_laser / "base_acrilico5_CORTADA.svg").read_text():
        print("  OJO: la placa cambió respecto de la que ya se cortó (base_acrilico5_CORTADA.svg)")
    print(f"base de acrílico: {aw:.0f} x {ah:.0f} mm (con margen), {len(ranuras())} ranuras")
    total = 0
    for viejo in ("soporte_brazo.stl", "brazo.stl"):
        (carpeta_stl / viejo).unlink(missing_ok=True)
    exportar = dict(piezas_impresas(), tapon=tapon())
    exportar.pop("gancho izquierdo")
    for n, p in exportar.items():
        nombre = n.replace(" del ", "_").replace(" ", "_")
        if nombre == "gancho_derecho":
            nombre = "gancho"
        cq.exporters.export(p, str(carpeta_stl / f"{nombre}.stl"), tolerance=0.05, angularTolerance=0.1)
        v = p.val().Volume() / 1000 * {"gancho": 2, "tapon": 10}.get(nombre, 1)
        total += v
        bb = p.val().BoundingBox()
        print(f"  {nombre:16s} {bb.xlen:6.1f} x {bb.ylen:6.1f} x {bb.zlen:5.1f} mm  {v:5.1f} cm³")
    print(f"  total impreso: {total:.0f} cm³")
    if "--revisar" in sys.argv:
        revisar()


def prueba_clips(carpeta_stl, carpeta_laser):
    """Tira de acrílico con ranuras de tres holguras y una pieza impresa con un clip de cada
    tamaño, para elegir la holgura antes de cortar la base."""
    global HOLGURA_CLIP
    huecos, x = [], 8.0
    for c in (CLIP, CLIP_CHICO):
        for h in (0.10, 0.15, 0.25):
            viejo, HOLGURA_CLIP = HOLGURA_CLIP, h
            _, _, ax, ay = ranura_clip(x, 10, "x", c)
            HOLGURA_CLIP = viejo
            huecos.append(srect(x - ax / 2, 10 - ay / 2, x + ax / 2, 10 + ay / 2))
            x += 14
    tira = srect(0, 0, x - 4, 20).difference(unary_union(huecos)).buffer(KERF / 2, join_style=2)
    alto = 26
    d = []
    for anillo in [tira.exterior] + list(tira.interiors):
        d.append('<path d="M ' + " L ".join(f"{px + 3:.3f},{alto - (py + 3):.3f}" for px, py in anillo.coords) + ' Z"/>')
    (carpeta_laser / "prueba_clips_acrilico5.svg").write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{x + 2:.1f}mm" height="{alto}mm" viewBox="0 0 {x + 2:.1f} {alto}">
<g id="corte" fill="none" stroke="#ff0000" stroke-width="0.1">
{chr(10).join(d)}
</g>
</svg>
''')
    base = caja(0, 30, 0, 14, -3, 0)
    pieza = base.union(clip(8, 7, 0, 1, "x", CLIP)).union(clip(22, 7, 0, 1, "x", CLIP_CHICO))
    cq.exporters.export(pieza, str(carpeta_stl / "prueba_clips.stl"), tolerance=0.05, angularTolerance=0.1)


if __name__ == "__main__" and "--pruebas" in sys.argv:
    prueba_clips(AQUI / "stl_base", AQUI / "laser")
