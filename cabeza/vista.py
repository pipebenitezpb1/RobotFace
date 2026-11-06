# Vista armada sobre el MacBook Air (render simple con z-buffer): mecanismo a la vista adelante,
# caja de la electrónica atrás, base de acrílico con piezas impresas encajadas.
# Uso: .venv-cad/bin/python cabeza/vista.py   ->  cabeza/vista.png
import sys, tempfile
from pathlib import Path
import numpy as np, trimesh, cadquery as cq
from PIL import Image
AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI))
import bandeja as b
import caja_electronica as ce

tmp = Path(tempfile.mkdtemp())


def malla(obj, nombre):
    f = tmp / f"{nombre}.stl"; cq.exporters.export(obj, str(f), tolerance=0.3, angularTolerance=0.3)
    m = trimesh.load(f)
    return m.subdivide_to_size(max_edge=12, max_iter=12)   # triángulos chicos: la profundidad sale bien


import base_acrilico as ba
todas, pantalla = b.armado("MacBook Air"); meca = b.mecanismo()
imp = ba.piezas_impresas()
union = None
for n, o in imp.items():
    union = o if union is None else union.union(o)
base = trimesh.load(AQUI / "eyemech_base.stl"); base.apply_translation(-base.bounds[0])
base.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [0, 0, 1]))
base.apply_translation([b.BASE_ANCHO / 2, b.Y_BASE, b.ALTURA_BASE])
pup = []
for sx in (-1, 1):
    p = trimesh.creation.icosphere(3, radius=7); p.apply_scale([1, 0.35, 1])
    p.apply_translation([sx * b.SEPARACION_OJOS / 2, b.Y_OJOS + b.DIAMETRO_OJO / 2 - 1.6, b.OJO_ALTURA]); pup.append(p)
NAR, GRIS, VIO = (0.93, 0.45, 0.15), (0.85, 0.85, 0.83), (0.33, 0.29, 0.72)
caja, sol = ce.caja_armada()
pantalla = b.pantalla(ba.GROSOR_PANTALLA, ba.INCLINACION_PANTALLA)   # la base siempre perpendicular a la pantalla
escena = [(malla(pantalla, "pantalla"), (0.15, 0.15, 0.17)),
          (malla(union, "impresas"), VIO),
          (malla(ba.placa_3d(), "acrilico_base"), (0.78, 0.88, 0.93)), (base, NAR), (malla(meca["pivotes de los párpados"], "pat"), NAR),
          (malla(meca["ojos"], "ojos"), (0.97, 0.97, 0.95)), (trimesh.util.concatenate(pup), (0.05, 0.05, 0.05)),
          (malla(caja.cut(sol["tapa"]), "mdf"), (0.74, 0.58, 0.40)), (malla(sol["tapa"], "acrilico"), (0.80, 0.90, 0.95))]
abierta = [e for e in escena[:-2]] + [(malla(meca["Arduino UNO"], "uno"), (0.1, 0.45, 0.6)),
                                     (malla(meca["PCA9685"], "pca"), (0.1, 0.25, 0.65))]


def render(sc, az, el, W=1100, H=800):
    a, e = np.radians(az), np.radians(el)
    d = np.array([np.cos(e) * np.sin(a), np.cos(e) * np.cos(a), np.sin(e)])
    f = -d; r = np.cross(f, [0, 0, 1]); r /= np.linalg.norm(r); u = np.cross(r, f)
    cam = np.array([0, -80, 0.]) + d * 750
    zb = np.full((H, W), np.inf); img = np.ones((H, W, 3)) * np.array([0.96, 0.96, 0.97])
    luz = -f * 0.4 + np.array([0.3, 0.5, 0.8]); luz /= np.linalg.norm(luz)
    for m, col in sc:
        v = m.vertices - cam; X = v @ r; Y = v @ u; Z = v @ f
        px = W / 2 + X * 2000 / Z; py = H / 2 - Y * 2000 / Z
        sh = np.clip(np.abs(m.face_normals @ luz) * 0.75 + 0.3, 0, 1.1)
        for t_, i in enumerate(m.faces):
            xs, ys, zs = px[i], py[i], Z[i]
            x0, x1 = int(max(0, np.floor(xs.min()))), int(min(W - 1, np.ceil(xs.max())))
            y0, y1 = int(max(0, np.floor(ys.min()))), int(min(H - 1, np.ceil(ys.max())))
            if x0 > x1 or y0 > y1: continue
            den = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
            if abs(den) < 1e-9: continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
            w0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / den
            w1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / den
            w2 = 1 - w0 - w1; msk = (w0 >= -1e-3) & (w1 >= -1e-3) & (w2 >= -1e-3)
            if not msk.any(): continue
            z = w0 * zs[0] + w1 * zs[1] + w2 * zs[2]
            sub = zb[y0:y1 + 1, x0:x1 + 1]; upd = msk & (z < sub)
            sub[upd] = z[upd]; img[y0:y1 + 1, x0:x1 + 1][upd] = np.array(col) * sh[t_]
    return Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))

vistas = [(escena, 35, 18), (abierta, 35, 30), (escena, 215, 20), (escena, 270, 2)]
ims = [render(sc, az, el) for sc, az, el in vistas]
lienzo = Image.new("RGB", (sum(i.width for i in ims), ims[0].height), "white"); x = 0
for i in ims: lienzo.paste(i, (x, 0)); x += i.width
lienzo.save(AQUI / "vista.png"); print(AQUI / "vista.png")
