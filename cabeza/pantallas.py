# Pantallas de ejemplo para revisar la montura, y utilidades comunes de los modelos.
import cadquery as cq

CAMARA_BAJO_BORDE = 4.0    # distancia del borde de arriba de la pantalla al centro de la cámara
ANCHO_LIBRE_CAMARA = 50.0  # zona central del frente de la pantalla que no se toca
EJEMPLOS = {               # grosor de la pantalla en el borde, cuánto se echa hacia atrás (°)
    "MacBook Air": (4.5, 15.0),
    "monitor": (30.0, 5.0),
}


def cilindro_x(radio, x0, x1, y, z):
    """Cilindro con el eje a lo largo de x (para bisagras y ejes)."""
    return cq.Workplane("YZ").circle(radio).extrude(x1 - x0).translate((x0, y, z))
