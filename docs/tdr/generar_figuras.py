from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
OUT = REPO / "outputs"
FIG = ROOT / "figures"
FIG.mkdir(parents=True, exist_ok=True)

PROB_FILE = REPO / "data" / "raw" / "MapProbabilidad_adulto.csv"
if not PROB_FILE.exists():
    raise FileNotFoundError(
        f"No existe {PROB_FILE}. El informe no usa una superficie sintética."
    )

PORTS = {
    "Malabrigo": (-79.44141666666667, -7.692789583333334),
    "Chimbote": (-78.9475, -9.075833333333334),
    "Callao": (-77.14027777777778, -12.045),
}

# Referencias visuales únicamente. No son geometrías oficiales SERNANP.
REFERENCE_EXCLUSIONS = [
    {"name": "Zona prohibida ref. 1", "lon": -79.05, "lat": -8.55, "radius": 0.16},
    {"name": "Zona prohibida ref. 2", "lon": -78.15, "lat": -10.45, "radius": 0.16},
    {"name": "Zona prohibida ref. 3", "lon": -77.05, "lat": -12.85, "radius": 0.18},
]

prob = pd.read_csv(PROB_FILE).dropna(subset=["Lon", "Lat", "Prob"])
zones = pd.read_csv(OUT / "zonas_candidatas.csv")
greedy = pd.read_csv(OUT / "asignacion_greedy.csv")
milp = pd.read_csv(OUT / "asignacion_milp.csv")
marl = pd.read_csv(OUT / "asignacion_marl.csv")
summary = pd.read_csv(OUT / "resumen_metodos.csv")
history = pd.read_csv(OUT / "historial_entrenamiento_marl.csv")

zone_lookup = zones.set_index("zone_id")


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIG / name, dpi=190, bbox_inches="tight", format="jpg")
    plt.close(fig)


def draw_reference_exclusions(ax):
    for ref in REFERENCE_EXCLUSIONS:
        circle = Circle(
            (ref["lon"], ref["lat"]),
            ref["radius"],
            fill=False,
            linewidth=1.3,
            linestyle="--",
        )
        ax.add_patch(circle)
        ax.annotate(
            ref["name"],
            (ref["lon"], ref["lat"]),
            xytext=(6, 5),
            textcoords="offset points",
            fontsize=7,
        )


def background(ax):
    sc = ax.scatter(
        prob["Lon"], prob["Lat"], c=prob["Prob"],
        s=7, alpha=.84, vmin=0, vmax=1
    )
    return sc


def detailed_map(assignments, title, filename, show_ids=True):
    fig, ax = plt.subplots(figsize=(8.7, 10))
    sc = background(ax)
    plt.colorbar(sc, ax=ax, label="Probabilidad de presencia de anchoveta")

    for name, (lon, lat) in PORTS.items():
        ax.scatter(lon, lat, marker="^", s=125)
        ax.annotate(name, (lon, lat), xytext=(5, 5),
                    textcoords="offset points", fontsize=9, fontweight="bold")

    ax.scatter(zones["Lon"], zones["Lat"], marker="x", s=48)
    for r in zones.itertuples(index=False):
        ax.annotate(f"Z{int(r.zone_id)}", (r.Lon, r.Lat),
                    xytext=(3, 3), textcoords="offset points", fontsize=6.5)

    draw_reference_exclusions(ax)

    if assignments is not None:
        for r in assignments.itertuples(index=False):
            z = zone_lookup.loc[int(r.zone_id)]
            plon, plat = PORTS[r.port]
            ax.plot([plon, z.Lon], [plat, z.Lat], linewidth=.75, alpha=.55)
            if show_ids:
                ax.annotate(
                    f"A{int(r.agent_id)}",
                    ((plon + z.Lon)/2, (plat + z.Lat)/2),
                    xytext=(2,2), textcoords="offset points", fontsize=6.5
                )

    ax.set_title(title)
    ax.set_xlabel("Longitud")
    ax.set_ylabel("Latitud")
    ax.grid(alpha=.18)
    ax.set_aspect("equal", adjustable="box")
    ax.text(
        .01, .01,
        "Fondo: MapProbabilidad_adulto.csv completo.\n"
        "Círculos: exclusiones ilustrativas; no SERNANP oficial.",
        transform=ax.transAxes, fontsize=7, va="bottom",
        bbox=dict(boxstyle="round", alpha=.65)
    )
    save(fig, filename)


# Mapas detallados sobre la grilla completa real del proyecto.
detailed_map(None, "Probabilidad + puertos + zonas candidatas", "mapa_detallado_probabilidad_puertos_zonas.jpg", False)
detailed_map(greedy, "Mapa detallado de asignación — Greedy", "mapa_detallado_greedy.jpg")
detailed_map(milp, "Mapa detallado de asignación — MILP", "mapa_detallado_milp.jpg")
detailed_map(marl, "Mapa detallado de asignación — MARL", "mapa_detallado_marl.jpg")
detailed_map(marl, "Asignación espacial MARL — grilla completa", "mapa_final_modelo.jpg")

# Comparación global.
for col, title, ylabel, name in [
    ("probabilidad_media", "Probabilidad media por método", "Probabilidad media", "probabilidad_metodos.jpg"),
    ("distancia_total_nm", "Distancia total por método", "Millas náuticas (ida + retorno)", "distancia_metodos.jpg"),
    ("combustible_total_l", "Combustible de referencia por método", "Litros estimados", "combustible_metodos.jpg"),
]:
    fig, ax = plt.subplots(figsize=(7.2,4.3))
    ax.bar(summary["metodo"], summary[col])
    ax.set_title(title)
    ax.set_xlabel("Método")
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=.2)
    save(fig, name)

fig, ax = plt.subplots(figsize=(7.2,4.3))
ax.bar(summary["metodo"], summary["costo_total_pen"])
ax.set_title("Costo referencial de combustible — S/ 5.00/L")
ax.set_xlabel("Método")
ax.set_ylabel("S/ (escenario)")
ax.grid(axis="y", alpha=.2)
save(fig, "costo_combustible_escenario.jpg")

# Ranking de zonas.
top = zones.sort_values("Prob", ascending=False).head(10)
fig, ax = plt.subplots(figsize=(8,4.4))
ax.bar(top["zone_id"].astype(int).astype(str), top["Prob"])
ax.set_title("Top 10 zonas candidatas por probabilidad")
ax.set_xlabel("Zona")
ax.set_ylabel("Probabilidad")
ax.grid(axis="y", alpha=.2)
save(fig, "top10_zonas_probabilidad.jpg")

# Ocupación por método.
all_assign = pd.concat([
    greedy.assign(metodo="Greedy"),
    milp.assign(metodo="MILP"),
    marl.assign(metodo="MARL"),
], ignore_index=True)
occ = all_assign.groupby(["metodo", "zone_id"]).size().rename("n").reset_index()
pivot = occ.pivot(index="zone_id", columns="metodo", values="n").fillna(0).sort_index()

fig, ax = plt.subplots(figsize=(10,4.7))
x = np.arange(len(pivot))
width = .25
methods = list(pivot.columns)
for i, method in enumerate(methods):
    ax.bar(x + (i-1)*width, pivot[method].values, width=width, label=method)
ax.set_xticks(x, pivot.index.astype(str))
ax.set_title("Ocupación de zonas por método")
ax.set_xlabel("Zona")
ax.set_ylabel("Número de barcos")
ax.grid(axis="y", alpha=.2)
ax.legend()
save(fig, "ocupacion_zonas_por_metodo.jpg")

# Diagnósticos MARL.
port = marl.groupby("port", as_index=False).agg(
    combustible=("combustible_total_l", "sum"),
    distancia=("distancia_total_nm", "sum"),
    probabilidad=("prob", "mean"),
)

fig, ax = plt.subplots(figsize=(7.2,4.3))
ax.bar(port["port"], port["combustible"])
ax.set_title("Combustible total por puerto — MARL")
ax.set_ylabel("Litros estimados")
ax.grid(axis="y", alpha=.2)
save(fig, "combustible_puerto_marl.jpg")

fig, ax = plt.subplots(figsize=(7.2,4.3))
ax.bar(port["port"], port["distancia"])
ax.set_title("Distancia total por puerto — MARL")
ax.set_ylabel("Millas náuticas")
ax.grid(axis="y", alpha=.2)
save(fig, "distancia_puerto_marl.jpg")

m = marl.sort_values("agent_id")
fig, ax = plt.subplots(figsize=(9.2,4.4))
ax.bar(m["agent_id"].astype(str), m["combustible_total_l"])
ax.set_title("Combustible estimado por barco — MARL")
ax.set_xlabel("Agente")
ax.set_ylabel("Litros estimados")
ax.grid(axis="y", alpha=.2)
save(fig, "combustible_barco_marl.jpg")

fig, ax = plt.subplots(figsize=(9.2,4.4))
ax.bar(m["agent_id"].astype(str), m["policy_reward"])
ax.set_title("Recompensa de política por barco — MARL")
ax.set_xlabel("Agente")
ax.set_ylabel("Policy reward")
ax.grid(axis="y", alpha=.2)
save(fig, "policy_reward_barco_marl.jpg")

occ_marl = marl.groupby("zone_id").size().sort_index()
fig, ax = plt.subplots(figsize=(8,4.3))
ax.bar(occ_marl.index.astype(str), occ_marl.values)
ax.set_title("Ocupación de zonas — MARL")
ax.set_xlabel("Zona")
ax.set_ylabel("Número de barcos")
ax.grid(axis="y", alpha=.2)
save(fig, "ocupacion_marl.jpg")

fig, ax = plt.subplots(figsize=(7,5))
ax.scatter(marl["distancia_total_nm"], marl["prob"], s=65)
for r in marl.itertuples(index=False):
    ax.annotate(str(r.agent_id), (r.distancia_total_nm, r.prob),
                xytext=(3,3), textcoords="offset points", fontsize=8)
ax.set_title("Trade-off distancia total vs probabilidad — MARL")
ax.set_xlabel("Distancia ida + retorno (NM)")
ax.set_ylabel("Probabilidad")
ax.grid(alpha=.2)
save(fig, "tradeoff_marl.jpg")

# Entrenamiento MARL sobre la misma grilla estática.
fig, ax = plt.subplots(figsize=(8.5,4.2))
ax.plot(history["update"], history["team_reward_real_grid"], linewidth=1, label="Recompensa media")
ax.plot(
    history["update"],
    history["team_reward_real_grid"].rolling(10, min_periods=1).mean(),
    linewidth=2.2, label="Media móvil 10"
)
ax.set_title("Entrenamiento MARL sobre MapProbabilidad_adulto.csv")
ax.set_xlabel("Actualización")
ax.set_ylabel("Recompensa de equipo")
ax.grid(alpha=.2)
ax.legend()
fig.tight_layout()
fig.savefig(FIG/"entrenamiento_marl.jpg", dpi=190, bbox_inches="tight")
fig.savefig(FIG/"entrenamiento_marl_detallado.jpg", dpi=190, bbox_inches="tight")
plt.close(fig)

# Montaje de simulación del plan final.
frames = [0., .33, .66, 1.]
fig, axes = plt.subplots(2,2,figsize=(10,10), sharex=True, sharey=True)
for ax, frac in zip(axes.flat, frames):
    ax.scatter(prob["Lon"], prob["Lat"], c=prob["Prob"], s=2.5, alpha=.28, vmin=0, vmax=1)
    for name,(lon,lat) in PORTS.items():
        ax.scatter(lon,lat,marker="^",s=80)
    for r in marl.itertuples(index=False):
        z = zone_lookup.loc[int(r.zone_id)]
        plon, plat = PORTS[r.port]
        x = plon + frac*(z.Lon-plon)
        y = plat + frac*(z.Lat-plat)
        ax.plot([plon,z.Lon],[plat,z.Lat],linewidth=.35,alpha=.15)
        ax.scatter(x,y,s=25)
    ax.set_title(f"Progreso simulado: {frac*100:.0f}%")
    ax.grid(alpha=.12)
    ax.set_aspect("equal", adjustable="box")
fig.suptitle("Simulación visual de los 15 agentes sobre la grilla completa", fontsize=14)
save(fig, "simulacion_montaje.jpg")

print("Figuras generadas desde outputs frescos y MapProbabilidad_adulto.csv")
