# Cápsula impresa para el módulo USB-C hembra (placa de 4 pads V, D-, D+, G) que alimenta los
# servos: una caja cerrada en dos mitades que encierra el módulo. Por adelante asoma solo el
# conector (por un hueco de la pared de atrás de la caja de la electrónica) y por atrás salen
# los cables. Se cierra con dos M3 verticales en las orejas de atrás y se atornilla a la pared
# con dos M3 + tuerca, que también aprietan las dos mitades.
#
# Medidas estimadas del módulo: ajustarlas con un pie de metro y volver a generar.
# Uso: .venv-cad/bin/python cabeza/usbc.py  ->  cabeza/stl_base/capsula_usbc.stl
import sys
from pathlib import Path
import cadquery as cq

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI))
import bandeja as b

# ---------------- Módulo (medidas típicas; confirmar) -----------------------------------------
PLACA = (10.6, 15.0, 1.6)        # ancho, largo, grosor de la placa azul
CONECTOR = (8.94, 7.35, 3.26)    # ancho, largo, alto del conector Type-C (estándar)
CONECTOR_SOBRE_PLACA = 0.8       # cuánto sobresale el conector por delante de la placa
ALTO_SOLDADURAS = 3.0            # espacio sobre los pads para los cables soldados
HOLGURA = 0.25                   # alrededor de la placa
HOLGURA_CONECTOR = 0.05          # el conector entra a presión en su forma redondeada

# ---------------- Cápsula -------------------------------------------------------------------
PARED = 2.0
PESTANA = (30.0, 12.1, 2.5)      # ancho, alto (= alto de la cápsula), grosor de la pestaña
SEPARACION_TORNILLOS = 22.0      # M3 a cada lado, con espacio para la tuerca
PASO_M3 = 3.4
ROSCA_M3 = 2.6                   # para que el M3 rosque firme en el plástico
APRIETE = 0.3                    # cuánto baja de más el relleno de la tapa para apretar el conector

# ---------------- Dónde va (en el mundo, ejes de bandeja.py) ---------------------------------
X_USBC = 3.0          # entre la UNO y la PCA9685
Z_USBC = 10.0         # altura del centro del conector sobre la bandeja


def _cuerpo_local():
    """Caja cerrada alrededor del módulo, con el conector mirando hacia -y (afuera de la caja),
    la cara de la pestaña en y=0 (contra la cara de adentro de la pared) y el centro del conector
    en x=0, z=0. Se parte en dos mitades por z=0 (ver mitades())."""
    cw, cl, ch = CONECTOR[0] + 2 * HOLGURA, CONECTOR[1], CONECTOR[2] + 2 * HOLGURA
    pw, pl, pt = PLACA[0] + 2 * HOLGURA, PLACA[1], PLACA[2] + 2 * HOLGURA
    y_placa0 = CONECTOR_SOBRE_PLACA - b.CAJA_PARED              # donde empieza la placa (en la pared)
    y_placa1 = y_placa0 + pl
    largo = y_placa1 + PARED                                    # pared de atrás (con salida de cables)
    alto_int = pt + 2 * ALTO_SOLDADURAS
    ancho_ext, alto_ext = pw + 2 * PARED, alto_int + 2 * PARED
    cuerpo = cq.Workplane("XY").box(ancho_ext, largo, alto_ext).translate((0, largo / 2, 0))
    cuerpo = cuerpo.union(cq.Workplane("XY").box(PESTANA[0], PESTANA[2], PESTANA[1]).translate((0, PESTANA[2] / 2, 0)))
    # Huecos: conector adelante; la placa sujeta por los cantos (rieles de 1,2 mm arriba y abajo);
    # al centro, espacio para las patas del conector y las soldaduras
    # El conector Type-C tiene los extremos redondos (forma de cápsula): el hueco copia esa forma,
    # apenas más grande, para que entre a presión
    cw_p, ch_p = CONECTOR[0] + 2 * HOLGURA_CONECTOR, CONECTOR[2] + 2 * HOLGURA_CONECTOR
    redondo = (cq.Workplane("XZ").slot2D(cw_p, ch_p).extrude(-(cl + 1))
               .translate((0, -b.CAJA_PARED - 0.5, 0)))
    cuerpo = cuerpo.cut(redondo)
    cuerpo = cuerpo.cut(cq.Workplane("XY").box(pw, pl, pt).translate((0, (y_placa0 + y_placa1) / 2, 0)))
    y_sold0 = cl - b.CAJA_PARED                                 # las soldaduras empiezan detrás del conector
    cuerpo = cuerpo.cut(cq.Workplane("XY").box(pw - 2.4, y_placa1 - y_sold0, alto_int)
                        .translate((0, (y_sold0 + y_placa1) / 2, 0)))
    # Salida de los cables por atrás, a lo ancho de los pads; los cantos de la placa topan en la
    # pared de atrás, así al enchufar no se va hacia adentro
    cuerpo = cuerpo.cut(cq.Workplane("XY").box(pw - 2.4, PARED * 3, alto_int).translate((0, largo, 0)))
    # Orejas a los lados, atrás, para el tornillo que cierra las dos mitades
    for sx in (-1, 1):
        oreja = cq.Workplane("XY").box(6, 6, alto_ext).translate((sx * (ancho_ext / 2 + 3), largo - 3, 0))
        cuerpo = cuerpo.union(oreja)
    # Tornillos de la pestaña (medio agujero en cada mitad) y tornillo vertical que cierra atrás
    for sx in (-1, 1):
        cuerpo = cuerpo.cut(cq.Workplane("XZ").circle(PASO_M3 / 2).extrude(-20).translate(
            (sx * SEPARACION_TORNILLOS / 2, -5, 0)))
    for sx in (-1, 1):   # tornillos que cierran: rosca justa en el cuerpo (la tapa se agranda en mitades())
        x_t = sx * (ancho_ext / 2 + 3)
        cuerpo = cuerpo.cut(cq.Workplane("XY").circle(ROSCA_M3 / 2).extrude(2 * alto_ext).translate((x_t, largo - 3, -alto_ext)))
    return cuerpo


def mitades():
    """(cuerpo, tapa). El cuerpo queda abierto arriba, del ancho de la placa: el módulo se mete
    desde arriba y se apoya en su cuna (riel de abajo de la placa y media forma redondeada del
    conector). La tapa es una placa plana con un relleno que baja y aprieta el conector y los
    cantos de la placa. Las dos se imprimen planas, sin soportes."""
    cw_p, ch_p = CONECTOR[0] + 2 * HOLGURA_CONECTOR, CONECTOR[2] + 2 * HOLGURA_CONECTOR
    pw, pl, pt = PLACA[0] + 2 * HOLGURA, PLACA[1], PLACA[2] + 2 * HOLGURA
    alto_int = pt + 2 * ALTO_SOLDADURAS
    alto_ext = alto_int + 2 * PARED
    z_corte = alto_int / 2                       # techo del hueco interior
    cl = CONECTOR[1]
    y_con1 = cl - b.CAJA_PARED
    y_placa1 = CONECTOR_SOBRE_PLACA - b.CAJA_PARED + pl
    G = 100
    c = _cuerpo_local()
    abertura = cq.Workplane("XY").box(pw, y_placa1 + 1, G).translate((0, (y_placa1 - 1) / 2, pt / 2 + G / 2))
    # Cuerpo: lo que está bajo el techo y la pestaña entera, menos la abertura de arriba
    cuerpo = c.intersect(cq.Workplane("XY").box(G, G, G).translate((0, 0, z_corte - G / 2)))
    cuerpo = cuerpo.union(c.intersect(cq.Workplane("XY").box(G, PESTANA[2], G).translate((0, PESTANA[2] / 2, 0))))
    cuerpo = cuerpo.cut(abertura)
    # Tapa: el techo (detrás de la pestaña) más el relleno de la abertura, menos los huecos
    techo = c.intersect(cq.Workplane("XY").box(G, G, G).translate((0, PESTANA[2] + G / 2, z_corte + G / 2)))
    relleno = abertura.intersect(cq.Workplane("XY").box(G, G, alto_ext).translate((0, G / 2, 0)))
    relleno = relleno.intersect(c.union(cq.Workplane("XY").box(pw, y_placa1, alto_ext).translate((0, y_placa1 / 2, 0))))
    relleno = relleno.cut(cq.Workplane("XZ").slot2D(cw_p, ch_p).extrude(-(cl + 2)).translate((0, -b.CAJA_PARED - 1, 0)))
    relleno = relleno.cut(cq.Workplane("XY").box(pw - 2.4, y_placa1 - y_con1, alto_int)
                          .translate((0, (y_con1 + y_placa1) / 2, 0)))
    holgura = cq.Workplane("XY").box(G, G, G).translate((0, G / 2, 0)).cut(
        cq.Workplane("XY").box(pw - 0.3, G, G).translate((0, G / 2, 0)))
    # El relleno baja APRIETE mm de más: al apretar los tornillos aprieta el conector y la placa
    tapa = techo.union(relleno.cut(holgura).translate((0, 0, -APRIETE)))
    # Agujeros de la tapa pasantes
    ancho_ext = pw + 2 * PARED
    largo = y_placa1 + PARED
    for sx in (-1, 1):
        tapa = tapa.cut(cq.Workplane("XY").circle(PASO_M3 / 2).extrude(G).translate((sx * (ancho_ext / 2 + 3), largo - 3, -G / 2)))
    return cuerpo, tapa


def capsula():
    """La cápsula en su lugar dentro de la caja."""
    y_pared = b.Y_CAJA_ATRAS_IN                                 # cara de adentro de la pared de atrás
    return _cuerpo_local().translate((X_USBC, y_pared, Z_USBC))   # el conector ya mira hacia afuera (-y)


def huecos_pared():
    """Huecos en la pared de atrás (en el mundo): (x, z, ancho, alto, radio) para el conector y
    (x, z, diámetro) para los dos tornillos."""
    alto = CONECTOR[2] + 0.4
    con = (X_USBC, Z_USBC, CONECTOR[0] + 0.4, alto, alto / 2 * 0.999)   # redondeado como el conector
    torn = [(X_USBC + sx * SEPARACION_TORNILLOS / 2, Z_USBC, PASO_M3) for sx in (-1, 1)]
    return con, torn


if __name__ == "__main__":
    salida = AQUI / "stl_base"
    salida.mkdir(exist_ok=True)
    for viejo in ("capsula_usbc.stl", "capsula_usbc_abajo.stl", "capsula_usbc_arriba.stl"):
        (salida / viejo).unlink(missing_ok=True)
    cuerpo, tapa = mitades()
    # Para imprimir: el cuerpo tal cual (base plana abajo); la tapa dada vuelta (cara de arriba abajo)
    for n, p_ in (("capsula_usbc_cuerpo", cuerpo), ("capsula_usbc_tapa", tapa.rotate((0, 0, 0), (1, 0, 0), 180))):
        cq.exporters.export(p_, str(salida / f"{n}.stl"), tolerance=0.05, angularTolerance=0.1)
        bb = p_.val().BoundingBox()
        print(f"{n:20s} {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm")
