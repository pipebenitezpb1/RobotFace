# Arma la página de entrega: copia las imágenes y genera las descargas (zip) a partir del proyecto.
# Nunca incluye la clave de la API ni datos de personas (caras, ropa, memoria, fotos de la cámara).
# Uso: .venv/bin/python web/armar.py   (después: pagina.command para verla en Chrome)
import shutil, subprocess, zipfile
from pathlib import Path

WEB = Path(__file__).resolve().parent
RAIZ = WEB.parent
IMG, DESC = WEB / "img", WEB / "descargas"
FOTOS = Path.home() / "Downloads"

# Nunca se publican (secretos y datos personales) ni se copian a los zip
PRIVADO = {"clave_anthropic.txt", "caras_conocidas.json", "personas.json", "memoria_robot.json",
           "conocimiento_escuela.md", "hablante.jpg", "caras.jpg", "camara_actual.jpg",
           "registro_seguir.txt", "registro_hablar.txt", "calibracion_habla.csv", "umbral_voz.txt",
           "ajuste_mirada.txt", "estado_seguir.json", "vista_web.jpg", "durmiendo", "saludar", "decir", "escaneando", "memoria_chat.md"}

CODIGO = ["seguir.py", "hablar.py", "serie.py", "seguir.command", "hablar.command", "calibrar.command",
          "cargar_arduino.command", "pagina.command", "servidor.py", "requisitos.txt", "requisitos_cad.txt", "calibracion.md",
          "README.md", "PROCESO_ENTREGA.md", "conocimiento_escuela.ejemplo.md", "descargar_modelos.sh", ".gitignore",
          "OjosAnimados/OjosAnimados.ino", "OjosCalibracion/OjosCalibracion.ino"]


def fotos():
    """Fotos del prototipo (HEIC del iPhone) a JPG livianos."""
    for nombre, destino in (("IMG_2116", "frente"), ("IMG_2112", "lado"), ("IMG_2117", "arriba"),
                            ("IMG_2114", "atras"), ("IMG_2119", "base"), ("IMG_0289", "prueba_mdf"),
                            ("IMG_2121", "boceto")):
        origen = FOTOS / f"{nombre}.HEIC"
        if origen.exists():
            subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "78", "-Z", "1500",
                            str(origen), "--out", str(IMG / f"{destino}.jpg")], capture_output=True)


def renders():
    for f in ("bocas_emociones.png", "capsula_usbc.png", "pata_mesa.png", "pata_lateral.png", "vista.png",
              "soporte_uno.png"):
        shutil.copy2(RAIZ / "cabeza" / f, IMG / f)
    for f in ("caja_mdf3.svg", "base_acrilico5.svg", "mapa_ranuras.png"):
        shutil.copy2(RAIZ / "cabeza" / "laser" / f, IMG / f)


def zip_de(nombre, archivos):
    with zipfile.ZipFile(DESC / nombre, "w", zipfile.ZIP_DEFLATED) as z:
        for ruta, en_zip in archivos:
            if ruta.name in PRIVADO:
                raise SystemExit(f"¡{ruta.name} es privado y no va en un zip!")
            z.write(ruta, en_zip)
    print(f"  {nombre}: {len(archivos)} archivos, {(DESC / nombre).stat().st_size / 1024:.0f} KB")


def descargas():
    cod = [(RAIZ / f, f"RobotFace/{f}") for f in CODIGO if (RAIZ / f).exists()]
    cad = sorted((RAIZ / "cabeza").glob("*.py"))
    cod += [(f, f"RobotFace/cabeza/{f.name}") for f in cad]
    zip_de("RobotFace_codigo.zip", cod)
    zip_de("RobotFace_piezas_3d.zip", [(f, f"piezas_3d/{f.name}") for f in sorted((RAIZ / "cabeza" / "stl_base").glob("*.stl"))])
    zip_de("RobotFace_corte_laser.zip", [(RAIZ / "cabeza" / "laser" / f, f"corte_laser/{f}") for f in
                                         ("base_acrilico5.svg", "caja_mdf3.svg", "prueba_ajuste_mdf3.svg")])
    shutil.copy2(RAIZ / "OjosAnimados" / "OjosAnimados.ino", DESC / "OjosAnimados.ino")
    shutil.copy2(RAIZ / "README.md", DESC / "README.md")


if __name__ == "__main__":
    IMG.mkdir(exist_ok=True)
    DESC.mkdir(exist_ok=True)
    fotos()
    renders()
    descargas()
    print("listo: abre pagina.command")
