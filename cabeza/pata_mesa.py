# Pata hasta la mesa: el peso del robot baja por una varilla roscada M8 hasta la mesa, detrás del
# computador, en vez de cargar la bisagra de la pantalla.
#   abrazadera_mesa.stl  se engancha en el borde de atrás de la base de acrílico (sin perforar):
#                        la varilla la empuja hacia arriba contra el acrílico y la pestaña de
#                        arriba evita que se caiga. Se imprime parada, sin soportes.
#   pie_mesa.stl         disco con tuerca M8 atrapada: girándolo se ajusta la altura (fieltro abajo).
# Ferretería: varilla roscada M8 de ~25 cm (cortarla a ~22 cm), 2 tuercas M8, fieltro.
# Uso: .venv-cad/bin/python cabeza/pata_mesa.py
import math
import sys
from pathlib import Path
import cadquery as cq

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI))
import bandeja as b
import base_acrilico as ba

ANCHO = 30.0
FONDO = 40.0                 # cuánto entra bajo el acrílico
ALTO = 25.0                  # bajo el acrílico
LABIO = 3.0                  # cuánto pasa la pestaña por encima del borde del acrílico
HOLGURA = 0.3
M8 = 8.4                     # agujero pasante
TUERCA_M8 = (13.3, 6.8)      # entre caras, alto
ALTURA_BORDE_MESA = 219.0    # borde de arriba de la pantalla sobre la mesa (MacBook Air 13,6" echado 15°)

Y_BORDE = ba.Y_PLACA[0]      # borde de atrás de la base de acrílico
Y_VARILLA = Y_BORDE + FONDO / 2


def hexagono(entre_caras, alto):
    r = entre_caras / 2 / math.cos(math.pi / 6)
    return cq.Workplane("XY").polygon(6, 2 * r).extrude(alto)


def abrazadera():
    za = -ba.ACRILICO
    bloque = b.caja(-ANCHO / 2, ANCHO / 2, Y_BORDE, Y_BORDE + FONDO, za - ALTO, za)
    atras = b.caja(-ANCHO / 2, ANCHO / 2, Y_BORDE - HOLGURA - 3.0, Y_BORDE - HOLGURA, za - ALTO, 2.0)
    labio = b.caja(-ANCHO / 2, ANCHO / 2, Y_BORDE - HOLGURA - 3.0, Y_BORDE + LABIO, HOLGURA, 2.0)
    sol = bloque.union(atras).union(labio)
    sol = sol.cut(cq.Workplane("XY").circle(M8 / 2).extrude(ALTO + 2).translate((0, Y_VARILLA, za - ALTO - 1)))
    return sol.cut(hexagono(*TUERCA_M8).translate((0, Y_VARILLA, za - ALTO - 0.01)))   # tuerca atrapada abajo


def pie():
    disco = cq.Workplane("XY").circle(20).extrude(7).edges(">Z").fillet(2)
    disco = disco.cut(cq.Workplane("XY").circle(M8 / 2).extrude(10).translate((0, 0, -1)))
    return disco.cut(hexagono(*TUERCA_M8).translate((0, 0, 7 - TUERCA_M8[1] + 0.01)))


def varilla():
    """Varilla en su lugar (para revisar), desde dentro de la abrazadera hasta el pie."""
    z_mesa = b.Z_PANTALLA - ALTURA_BORDE_MESA
    z_arriba = -ba.ACRILICO - 0.5
    return cq.Workplane("XY").circle(4).extrude(z_arriba - (z_mesa + 7)).translate((0, Y_VARILLA, z_mesa + 7))


def largo_varilla():
    return (-ba.ACRILICO - 0.5) - (b.Z_PANTALLA - ALTURA_BORDE_MESA + 1)


if __name__ == "__main__":
    salida = AQUI / "stl_base"
    a = abrazadera()
    cq.exporters.export(a, str(salida / "abrazadera_mesa.stl"), tolerance=0.05, angularTolerance=0.1)
    cq.exporters.export(pie(), str(salida / "pie_mesa.stl"), tolerance=0.05, angularTolerance=0.1)
    bb = a.val().BoundingBox()
    print(f"abrazadera_mesa {bb.xlen:.0f} x {bb.ylen:.0f} x {bb.zlen:.0f} mm, {a.val().Volume() / 1000:.0f} cm³")
    print(f"varilla M8: unos {largo_varilla():.0f} mm (comprar 25 cm y cortar; el pie regula ±1 cm)")
    import base_acrilico, caja_electronica as ce, usbc, pantallas
    otros = dict(base_acrilico.piezas_impresas(), acrilico=base_acrilico.placa_3d(), caja=ce.caja_armada()[0],
                 capsula=usbc.capsula(), pantalla=b.pantalla(base_acrilico.GROSOR_PANTALLA, base_acrilico.INCLINACION_PANTALLA))
    hubo = False
    for n, o in otros.items():
        for nn, mio in (("abrazadera", a), ("varilla", varilla())):
            v = o.intersect(mio).val().Volume()
            if v > 1:
                hubo = True; print(f"  choque: {nn} con {n}: {v:.0f} mm³")
    print("  sin choques" if not hubo else "")
