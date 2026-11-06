# Caja de la electrónica para cortar en láser: 5 caras de MDF de 3 mm con uniones dentadas y un
# grabado de surcos de cerebro en todas las caras de afuera. Va atrás en la bandeja (bandeja.py), sobre la Arduino UNO y la
# PCA9685; el mecanismo de ojos queda a la vista adelante.
#
# Uso:  .venv-cad/bin/python cabeza/caja_electronica.py [--revisar]
#   -> cabeza/laser/caja_paredes_mdf3.svg   4 paredes (rojo = corte, azul = nombres, opcional)
#   -> cabeza/laser/caja_tapa_acrilico5.svg tapa
#
# Medidas en mm. Mismos ejes que bandeja.py: z hacia arriba, y hacia adelante, x a los lados;
# z=0 es la cara de arriba de la bandeja.
import sys
from pathlib import Path
from shapely.geometry import box as rect, Polygon, Point
from shapely.ops import unary_union
from shapely import affinity

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI))
import bandeja as b

GROSOR = b.CAJA_PARED  # MDF de las paredes
GROSOR_TAPA = 3.0      # tapa de MDF, igual que las paredes
KERF = 0.0             # compensación del láser en MDF (con 0,15 quedaba muy apretado)
KERF_ACRILICO = 0.15
DIENTE = 12.0          # largo aproximado de cada diente
ALTO_LIBRE = 40.0      # por dentro: las placas (~23 mm) y los cables enchufados arriba de la PCA9685
PASO_CABLES = (60.0, 14.0)   # muesca abajo en el frente, para los cables de los servos
DIENTE_BASE = (15.0, 5.0)    # dientes de abajo de las paredes: ancho y largo (= grosor de la base de acrílico)

X_IN, Y_FRENTE_IN, Y_ATRAS_IN = b.X_CAJA_IN, b.Y_CAJA_FRENTE_IN, b.Y_CAJA_ATRAS_IN
W = 2 * X_IN + 2 * GROSOR
D = (Y_FRENTE_IN - Y_ATRAS_IN) + 2 * GROSOR
H = ALTO_LIBRE + GROSOR_TAPA
Y_FRENTE = Y_FRENTE_IN + GROSOR
t = GROSOR


def tramos(largo):
    n = max(3, int(round(largo / DIENTE)))
    if n % 2 == 0:
        n += 1
    return [(i * largo / n, (i + 1) * largo / n) for i in range(n)]


def entallas(largo, cuales, borde, alto_panel, ancho_panel, a_lo_largo_de, t=GROSOR):
    """Rectángulos de t de profundidad a quitar en un borde. `cuales` = 'pares' o 'impares'."""
    out = []
    for i, (a, c) in enumerate(tramos(largo)):
        if (i % 2 == 0) != (cuales == "pares"):
            continue
        if a_lo_largo_de == "u":       # borde horizontal (v=0 o v=alto)
            v0 = 0 if borde == "abajo" else alto_panel - t
            out.append(rect(a, v0, c, v0 + t))
        else:                           # borde vertical (u=0 o u=ancho)
            u0 = 0 if borde == "izq" else ancho_panel - t
            out.append(rect(u0, a, u0 + t, c))
    return out


def redondeado(cx, cy, ancho, alto, r):
    return rect(cx - ancho / 2 + r, cy - alto / 2 + r, cx + ancho / 2 - r, cy + alto / 2 - r).buffer(r, 16)


def panel_pared(ancho):
    """Frente o atrás (ancho = W) o lado (ancho = D), en coordenadas (u, v=z).
    Los dientes del borde de arriba entran en la tapa; los de los cantos verticales, entre sí."""
    p = rect(0, 0, ancho, H)
    quitar = entallas(ancho, "pares", "arriba", H, ancho, "u", GROSOR_TAPA)   # ahí van los dientes de la tapa
    lado = "impares" if ancho == W else "pares"                     # frente/atrás tienen las puntas
    for borde in ("izq", "der"):
        quitar += entallas(H, lado, borde, H, ancho, "v")
    p = p.difference(unary_union(quitar))
    # Dientes abajo, que entran en las ranuras de la base de acrílico
    return unary_union([p] + [rect(c - DIENTE_BASE[0] / 2, -DIENTE_BASE[1], c + DIENTE_BASE[0] / 2, 0.01)
                              for c in dientes_base(ancho)])


def dientes_base(ancho):
    """Centros (en u) de los dientes de abajo de una pared."""
    if ancho == W:
        return [W / 2 - 60]          # uno por pared basta para ubicar la caja
    return [0.5 * D]


def ranuras_base(holgura=0.15):
    """Ranuras en la base de acrílico para los dientes de abajo de las paredes: (x, y, ancho_x, largo_y)."""
    a, e = DIENTE_BASE[0] + 2 * holgura, GROSOR + 2 * holgura
    out = []
    for c in dientes_base(W):
        x = c - W / 2
        out += [(x, Y_FRENTE - GROSOR / 2, a, e), (-x, Y_FRENTE - D + GROSOR / 2, a, e)]   # la de atrás va volteada
    for c in dientes_base(D):
        for sx in (-1, 1):
            out.append((sx * (W / 2 - GROSOR / 2), Y_FRENTE - c, e, a))
    return out


def panel_tapa():
    """Tapa en coordenadas (u=x desde la izquierda, v desde el frente hacia atrás)."""
    p = rect(0, 0, W, D)
    quitar = entallas(W, "impares", "abajo", D, W, "u") + entallas(W, "impares", "arriba", D, W, "u")
    quitar += entallas(D, "impares", "izq", D, W, "v") + entallas(D, "impares", "der", D, W, "v")
    return p.difference(unary_union(quitar))


def piezas():
    # Frente: muesca abajo al centro y dos pasos más a los lados para los cables de los servos
    frente = panel_pared(W).difference(unary_union(
        [redondeado(W / 2, 0, PASO_CABLES[0], 2 * PASO_CABLES[1], 4)] +
        [redondeado(W / 2 + sx * 52, 14, 24, 10, 5) for sx in (-1, 1)]))
    atras = panel_pared(W)   # visto desde afuera (x al revés): USB y jack de la UNO, y la salida de cables
    z_placa = b.SEPARADOR + 1.6
    # Módulo USB-C de la alimentación de los servos (cápsula de usbc.py): hueco del conector y
    # los dos tornillos M3 de su pestaña
    import usbc
    (cx, cz, cw, ch, cr), tornillos = usbc.huecos_pared()
    huecos = [redondeado(W / 2 - cx, cz, cw, ch, cr)]
    huecos += [Point(W / 2 - x, z).buffer(d / 2, 24) for x, z, d in tornillos]
    for centro, ancho_, alto_ in ((b.UNO_USB[0], b.UNO_USB[1], b.UNO_USB[2]), b.UNO_JACK):
        x = b.x_uno(centro)
        huecos.append(redondeado(W / 2 - x, z_placa + alto_ / 2, ancho_ + 2, alto_ + 2, 1.5))
    atras = atras.difference(unary_union(huecos))
    lado = panel_pared(D)
    return {"frente": frente, "atrás": atras, "lado izquierdo": lado, "lado derecho": lado, "tapa": panel_tapa()}


def compensar(p, kerf=KERF):
    return p.buffer(kerf / 2, join_style=2)


def svg(todas, archivo, orden, kerf):
    """Hoja para el láser con las piezas de `orden` = [(nombre, dx, dy)]: rojo = corte,
    azul = nombres (para grabar o ignorar)."""
    margen = 3.0
    cajas = [affinity.translate(compensar(todas[n], kerf), dx + margen, dy + margen) for n, dx, dy in orden]
    ancho_hoja = max(p.bounds[2] for p in cajas) + margen
    alto_hoja = max(p.bounds[3] for p in cajas) + margen
    trazos, textos = [], []
    for (nombre, _, _), p in zip(orden, cajas):
        for anillo in [p.exterior] + list(p.interiors):
            d = "M " + " L ".join(f"{x:.3f},{alto_hoja - y:.3f}" for x, y in anillo.coords) + " Z"
            trazos.append(f'<path d="{d}"/>')
        bx = p.bounds
        textos.append(f'<text x="{(bx[0] + bx[2]) / 2:.1f}" y="{alto_hoja - bx[3] + 10:.1f}">{nombre}</text>')
    archivo.write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{ancho_hoja:.2f}mm" height="{alto_hoja:.2f}mm" viewBox="0 0 {ancho_hoja:.2f} {alto_hoja:.2f}">
<g id="corte" fill="none" stroke="#ff0000" stroke-width="0.1">
{chr(10).join(trazos)}
</g>
<g id="nombres" fill="#0000ff" font-family="Helvetica" font-size="5" text-anchor="middle">
{chr(10).join(textos)}
</g>
</svg>
''')
    return ancho_hoja, alto_hoja


# ---------------- Grabado: surcos de cerebro ------------------------------------------------
LARGO_SURCO = 14.0     # distancia típica entre surcos (mm)
MARGEN_GRABADO = 4.5   # sin grabado cerca de los bordes, dientes y agujeros


def cerebro(panel, semilla, hemisferios=False):
    """Líneas de surcos tipo cerebro dentro de `panel` (coordenadas del panel): curvas de nivel
    de una suma de ondas en todas direcciones (un laberinto parejo, como las circunvoluciones).
    Con hemisferios=True la mitad derecha es el espejo de la izquierda y hay una cisura al medio."""
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from shapely.geometry import LineString, box as caja_
    rng = np.random.default_rng(semilla)
    x0, y0, x1, y1 = panel.bounds
    xs, ys = np.arange(x0, x1, 0.5), np.arange(y0, y1, 0.5)
    X, Y = np.meshgrid(xs, ys)
    if hemisferios:
        X = (x0 + x1) / 2 - np.abs(X - (x0 + x1) / 2)
    k = 2 * np.pi / LARGO_SURCO
    Xw = X + 3.0 * np.sin(Y / 17 + rng.uniform(0, 6))     # una deformación suave, para que no sea regular
    Yw = Y + 3.0 * np.sin(X / 19 + rng.uniform(0, 6))
    Z = np.zeros_like(X)
    for _ in range(36):
        a = rng.uniform(0, np.pi)
        Z += np.cos(k * (np.cos(a) * Xw + np.sin(a) * Yw) + rng.uniform(0, 2 * np.pi))
    s_ = Z.std()
    fig = plt.figure()
    cs = plt.contour(X if not hemisferios else np.meshgrid(xs, ys)[0], Y, Z, levels=[-0.35 * s_, 0.35 * s_])
    plt.close(fig)
    zona = panel.buffer(-MARGEN_GRABADO, join_style=2)
    zona = zona.difference(unary_union([Polygon(h).buffer(MARGEN_GRABADO - 1) for h in panel.interiors])) \
        if panel.interiors else zona
    if hemisferios:
        medio = (x0 + x1) / 2
        cisura = LineString([(medio, y0 + 8), (medio, y1 - 8)])
        zona = zona.difference(cisura.buffer(2.0))
    lineas = []
    for nivel in cs.allsegs:
        for seg in nivel:
            if len(seg) < 4:
                continue
            l = LineString(seg).simplify(0.12).intersection(zona)
            for parte in getattr(l, "geoms", [l]):
                if parte.geom_type == "LineString" and parte.length > 3:
                    lineas.append(parte)
    if hemisferios:
        lineas.append(cisura)
    return lineas


def grabados(todas):
    sem = {"frente": 1, "atrás": 2, "lado izquierdo": 3, "lado derecho": 4, "tapa": 5}
    return {n: cerebro(todas[n], sem[n], hemisferios=(n == "tapa")) for n in sem}


def svg_mdf(todas, archivo, orden, kerf):
    """Una hoja con las piezas de `orden` = [(nombre, dx, dy)]: rojo = corte, azul = grabado."""
    margen = 3.0
    surcos = grabados(todas)
    # El frente y el de atrás se dibujan vistos desde AFUERA (con la cara grabada hacia afuera los
    # dientes y agujeros quedan en su lugar): se reflejan respecto de su centro.
    todas = dict(todas)
    for n in ("frente", "atrás"):
        todas[n] = affinity.scale(todas[n], xfact=-1, origin=(W / 2, 0))
        surcos[n] = [affinity.scale(l, xfact=-1, origin=(W / 2, 0)) for l in surcos[n]]
    cajas = [affinity.translate(compensar(todas[n], kerf), dx, dy) for n, dx, dy in orden]
    mx, my = min(p.bounds[0] for p in cajas), min(p.bounds[1] for p in cajas)   # los dientes de abajo bajan de 0
    orden = [(n, dx - mx + margen, dy - my + margen) for n, dx, dy in orden]
    cajas = [affinity.translate(p, -mx + margen, -my + margen) for p in cajas]
    ancho_hoja = max(p.bounds[2] for p in cajas) + margen
    alto_hoja = max(p.bounds[3] for p in cajas) + margen
    cortes, grabado = [], []
    for (nombre, dx, dy), p in zip(orden, cajas):
        for anillo in [p.exterior] + list(p.interiors):
            cortes.append('<path d="M ' + " L ".join(f"{x:.2f},{alto_hoja - y:.2f}" for x, y in anillo.coords) + ' Z"/>')
        for l in surcos[nombre]:
            l = affinity.translate(l, dx, dy)
            grabado.append('<path d="M ' + " L ".join(f"{x:.2f},{alto_hoja - y:.2f}" for x, y in l.coords) + '"/>')
    archivo.write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{ancho_hoja:.2f}mm" height="{alto_hoja:.2f}mm" viewBox="0 0 {ancho_hoja:.2f} {alto_hoja:.2f}">
<g id="grabado" fill="none" stroke="#0000ff" stroke-width="0.1">
{chr(10).join(grabado)}
</g>
<g id="corte" fill="none" stroke="#ff0000" stroke-width="0.1">
{chr(10).join(cortes)}
</g>
</svg>
''')
    return ancho_hoja, alto_hoja, len(grabado)


def armado(todas):
    """Las 5 caras como sólidos en su lugar (sin compensar el kerf), para revisar."""
    import cadquery as cq

    def solido(poly, e=t):
        w = cq.Workplane("XY").polyline(list(poly.exterior.coords)[:-1]).close().extrude(e)
        for h in poly.interiors:
            w = w.cut(cq.Workplane("XY").polyline(list(h.coords)[:-1]).close().extrude(e))
        return w

    def a_xz(sol, y0):           # (u, v, w) -> (x = u - W/2, y = y0 - w, z = v)
        return sol.rotate((0, 0, 0), (1, 0, 0), 90).translate((-W / 2, y0, 0))

    out = {}
    out["frente"] = a_xz(solido(todas["frente"]), Y_FRENTE)
    out["atrás"] = a_xz(solido(todas["atrás"]).mirror("YZ", (W / 2, 0, 0)), Y_FRENTE - D + t)
    lado = solido(todas["lado izquierdo"])     # (u = desde el frente, v = z)
    lado = lado.rotate((0, 0, 0), (1, 0, 0), 90).rotate((0, 0, 0), (0, 0, 1), -90)
    out["lado izquierdo"] = lado.translate((-W / 2 + t, Y_FRENTE, 0))
    out["lado derecho"] = lado.translate((W / 2, Y_FRENTE, 0))
    tapa = solido(todas["tapa"], GROSOR_TAPA).mirror("XZ").translate((-W / 2, Y_FRENTE, H - GROSOR_TAPA))
    out["tapa"] = tapa
    return out


def prueba_kerf(archivo, kerfs=(0.0, 0.05, 0.10)):
    """Tres pares de piezas chicas con una unión dentada, cada par con otra compensación de kerf,
    para elegir la que encaja justo antes de cortar la caja."""
    piezas_, x = [], 3.0
    for k in kerfs:
        a_ = rect(0, 0, 36, 20).difference(unary_union([rect(i * 12, 20 - GROSOR, i * 12 + 12, 20) for i in (0, 2)]))
        b2 = rect(0, 0, 36, 20).difference(unary_union([rect(12, 20 - GROSOR, 24, 20)]))
        for p_, dy in ((a_, 3.0), (b2, 28.0)):
            piezas_.append((affinity.translate(p_.buffer(k / 2, join_style=2), x, dy), k))
        x += 44
    alto = 54.0
    cortes, textos = [], []
    for p_, k in piezas_:
        cortes.append('<path d="M ' + " L ".join(f"{px:.3f},{alto - py:.3f}" for px, py in p_.exterior.coords) + ' Z"/>')
    for i, k in enumerate(kerfs):
        textos.append(f'<text x="{3 + 44 * i + 18:.1f}" y="{alto - 10:.1f}">{k:.2f}</text>')
    archivo.write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{x:.1f}mm" height="{alto}mm" viewBox="0 0 {x:.1f} {alto}">
<g id="grabado" fill="#0000ff" font-family="Helvetica" font-size="5" text-anchor="middle">
{chr(10).join(textos)}
</g>
<g id="corte" fill="none" stroke="#ff0000" stroke-width="0.1">
{chr(10).join(cortes)}
</g>
</svg>
''')


def caja_armada():
    sol = armado(piezas())
    caja = sol["frente"]
    for n in list(sol)[1:]:
        caja = caja.union(sol[n])
    return caja, sol


if __name__ == "__main__":
    import cadquery as cq
    carpeta = AQUI / "laser"
    carpeta.mkdir(exist_ok=True)
    todas = piezas()
    sep = 10.0
    for viejo in ("caja_paredes_mdf3.svg", "caja_tapa_acrilico5.svg"):
        (carpeta / viejo).unlink(missing_ok=True)
    aw, ah, ng = svg_mdf(todas, carpeta / "caja_mdf3.svg",
                         [("frente", 0, 0), ("atrás", 0, H + sep), ("lado izquierdo", W + sep, 0),
                          ("lado derecho", W + sep, H + sep), ("tapa", 0, 2 * (H + sep))], KERF)
    print(f"caja de la electrónica por fuera: {W:.1f} x {D:.1f} x {H:.1f} mm, todo MDF {GROSOR} mm")
    print(f"  hoja {aw:.0f} x {ah:.0f} mm, {ng} líneas de grabado")
    prueba_kerf(carpeta / "prueba_ajuste_mdf3.svg")
    if "--revisar" in sys.argv:
        caja, sol = caja_armada()
        nombres = list(sol)
        for i in range(len(nombres)):
            for j in range(i + 1, len(nombres)):
                v = sol[nombres[i]].intersect(sol[nombres[j]]).val().Volume()
                if v > 0.5:
                    print(f"  se pisan: {nombres[i]} y {nombres[j]}: {v:.1f} mm³")
        cq.exporters.export(caja, str(carpeta / "caja_electronica_armada.stl"))
        b.revisar(cubierta_=caja)
