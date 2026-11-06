# Plano con medidas: bandeja, ganchos, brazo y caja de la electrónica, con la base real del EyeMech.
# Uso: .venv-cad/bin/python cabeza/plano.py   ->  cabeza/plano.png
import sys
from pathlib import Path
import numpy as np, trimesh, cadquery as cq, tempfile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI))
import bandeja as b
import caja_electronica as ce

tmp = Path(tempfile.mkdtemp())
def malla(obj, n):
    f = tmp / f"{n}.stl"; cq.exporters.export(obj, str(f), tolerance=0.1, angularTolerance=0.2); return trimesh.load(f)

import base_acrilico as ba
todas, pantalla = b.armado("MacBook Air")
imp = ba.piezas_impresas()
todas["bandeja"] = ba.placa_3d()
todas.pop("soporte del brazo", None); todas.pop("brazo", None)
pantalla = b.pantalla(ba.GROSOR_PANTALLA, ba.INCLINACION_PANTALLA)
for n in ("gancho izquierdo", "gancho derecho", "pata trasera"):
    todas[n] = imp[n]
for n in ("cuna_izquierda", "cuna_derecha", "cuna_atras", "soporte_uno", "soporte_pca"):
    todas[n] = imp[n]
caja, _ = ce.caja_armada()
m = {n: malla(o, n) for n, o in dict(todas, caja=caja, pantalla=pantalla).items()}
base = trimesh.load(AQUI / "eyemech_base.stl"); base.apply_translation(-base.bounds[0])
base.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [0, 0, 1]))
base.apply_translation([b.BASE_ANCHO / 2, b.Y_BASE, b.ALTURA_BASE])

def corte(ax, mm_, normal, origen, ejes, **kw):
    for s in trimesh.intersections.mesh_plane(mm_, normal, origen):
        ax.plot(s[:, ejes[0]], s[:, ejes[1]], **kw)

def cota(ax, p0, p1, texto, off=(0, 0), color="#c0392b"):
    ax.annotate("", p0, p1, arrowprops=dict(arrowstyle="<->", color=color, lw=0.9))
    ax.text((p0[0] + p1[0]) / 2 + off[0], (p0[1] + p1[1]) / 2 + off[1], texto, color=color, fontsize=8,
            ha="center", va="center", bbox=dict(fc="white", ec="none", pad=0.5))

COL = {"bandeja": "#7f8c8d", "caja": "#8e5b2e", "pantalla": "#2c3e50", "gancho izquierdo": "#5b4bb7",
       "gancho derecho": "#5b4bb7", "pata trasera": "#5b4bb7",
       "cuna_izquierda": "#5b4bb7", "cuna_derecha": "#5b4bb7", "cuna_atras": "#5b4bb7",
       "soporte_uno": "#5b4bb7", "soporte_pca": "#5b4bb7"}
fig, axs = plt.subplots(1, 2, figsize=(18, 7.5))

# 1) De lado: corte por un gancho (x = GANCHO_X) y por el brazo (x = 0), superpuestos
ax = axs[0]
for n, c in COL.items():
    for x in (-2.0, b.GANCHO_X):
        corte(ax, m[n], [1, 0, 0], [x + 0.01, 0, 0], (1, 2), color=c, lw=0.9)
corte(ax, base, [1, 0, 0], [-b.SEPARACION_OJOS / 2, 0, 0], (1, 2), color="#e67e22", lw=0.6)
ax.add_patch(Circle((b.Y_OJOS, b.OJO_ALTURA), b.DIAMETRO_OJO / 2, fc="#ecf0f1", ec="k", lw=0.8))
ax.axvline(0, color="#3498db", lw=0.8, ls=":")
ax.text(2, -60, "frente de\nla pantalla", color="#3498db", fontsize=7)
cota(ax, (8, 0), (8, b.OJO_ALTURA), f"{b.OJO_ALTURA:.1f}", (5, 0))
cota(ax, (12, b.Z_PANTALLA), (12, 0), f"{-b.Z_PANTALLA:.0f}", (5, 0))
cota(ax, (ce.Y_FRENTE - ce.D, ce.H + 6), (ce.Y_FRENTE, ce.H + 6), f"caja {ce.D:.0f}", (0, 3))
cota(ax, (ce.Y_FRENTE - ce.D - 6, 0), (ce.Y_FRENTE - ce.D - 6, ce.H), f"{ce.H:.0f}", (-5, 0))
yb0, yb1 = b.Y_CAJA_ATRAS_IN - b.CAJA_PARED, b.Y_BANDEJA_FRENTE
yb0 = ba.Y_PLACA[0]
cota(ax, (yb0, -32), (yb1, -32), f"base de acrílico {yb1 - yb0:.0f}", (0, -3))
ax.text(-60, b.Z_PANTALLA - 30, "pata fija", color="#5b4bb7", fontsize=8)
ax.set_title("De lado: los ojos quedan al ras del frente de la pantalla")

# 2) Desde arriba
ax = axs[1]
corte(ax, m["bandeja"], [0, 0, 1], [0, 0, -2.5], (0, 1), color="#5dade2", lw=0.8)
corte(ax, m["caja"], [0, 0, 1], [0, 0, 20], (0, 1), color=COL["caja"], lw=1)
corte(ax, base, [0, 0, 1], [0, 0, b.ALTURA_BASE + 1], (0, 1), color="#e67e22", lw=0.6)
for n in ("gancho izquierdo", "gancho derecho", "pata trasera"):
    corte(ax, m[n], [0, 0, 1], [0, 0, -8], (0, 1), color=COL[n], lw=0.9)
for sx in (-1, 1):
    ax.add_patch(Circle((sx * b.SEPARACION_OJOS / 2, b.Y_OJOS), b.DIAMETRO_OJO / 2, fc="#ecf0f1", ec="k", lw=0.8))
pl, pa = b.PCA_PLACA; ul, ua = b.UNO_PLACA
ax.add_patch(Rectangle((b.PCA_X - pa / 2, b.Y_PCA - pl / 2), pa, pl, fc="#d6eaf8", ec="#2471a3", lw=0.8))
ax.add_patch(Rectangle((b.UNO_X, b.Y_USB), ua, ul, fc="#d5f5e3", ec="#1e8449", lw=0.8))
ax.text(b.UNO_X + ua / 2, b.Y_USB + ul / 2, "UNO", ha="center", fontsize=7, color="#1e8449")
ax.text(b.PCA_X, b.Y_PCA, "PCA9685", ha="center", fontsize=7, color="#2471a3", rotation=90)
ax.axhline(0, color="#3498db", lw=0.8, ls=":")
cota(ax, (-ce.W / 2, ce.Y_FRENTE - ce.D - 8), (ce.W / 2, ce.Y_FRENTE - ce.D - 8), f"{ce.W:.1f}", (0, -4))
cota(ax, (-b.GANCHO_X, 12), (b.GANCHO_X, 12), f"ganchos a {2 * b.GANCHO_X:.0f} (cámara libre al centro)", (0, 4), color="#5b4bb7")
ax.set_title("Desde arriba (naranjo: base real del EyeMech; morado: piezas impresas)")

for ax in axs:
    (a0, a1), (b0, b1) = ax.get_xlim(), ax.get_ylim()
    ax.set_xlim(a0 - 12, a1 + 12); ax.set_ylim(b0 - 12, b1 + 12)
    ax.set_aspect("equal"); ax.grid(True, lw=0.2); ax.tick_params(labelsize=7)
fig.suptitle("Montura del EyeMech: mecanismo a la vista, base de acrílico de 5 mm con piezas impresas — medidas en mm", fontsize=12)
plt.tight_layout(); plt.savefig(AQUI / "plano.png", dpi=110); print("listo")
