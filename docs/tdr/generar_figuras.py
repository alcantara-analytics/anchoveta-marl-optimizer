from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
FIG = ROOT / "figures"
FIG.mkdir(parents=True, exist_ok=True)

PORTS = {
    "Malabrigo": (-79.44141666666667, -7.692789583333334),
    "Chimbote": (-78.9475, -9.075833333333334),
    "Callao": (-77.14027777777778, -12.045),
}

# Zonas circulares usadas SOLO como referencia visual en los mapas.
# No representan geometrías oficiales SERNANP.
REFERENCE_EXCLUSIONS = [
    {"name": "Zona prohibida ref. 1", "lon": -79.05, "lat": -8.55, "radius": 0.16},
    {"name": "Zona prohibida ref. 2", "lon": -78.15, "lat": -10.45, "radius": 0.16},
    {"name": "Zona prohibida ref. 3", "lon": -77.05, "lat": -12.85, "radius": 0.18},
]

comparison = pd.read_csv(DATA / "comparison.csv")
greedy = pd.read_csv(DATA / "greedy.csv")
milp = pd.read_csv(DATA / "milp.csv")
marl = pd.read_csv(DATA / "marl_assignment.csv")
zones = pd.read_csv(DATA / "zones.csv")
history = pd.read_csv(DATA / "training_history.csv")

zone_lookup = zones.set_index("zone_id")


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIG / name, dpi=180, bbox_inches="tight", format="jpg")
    plt.close(fig)


def background_probability(ax):
    """
    Si el archivo real está disponible localmente, usa la grilla real.
    En GitHub público no se publica el archivo cliente; entonces se muestra
    una superficie visual interpolada desde las zonas candidatas y se etiqueta
    explícitamente como aproximación gráfica.
    """
    raw_candidates = [
        ROOT.parent.parent / "data" / "raw" / "MapProbabilidad_adulto.csv",
        ROOT.parent.parent / "data" / "MapProbabilidad_adulto.csv",
    ]
    raw = next((p for p in raw_candidates if p.exists()), None)

    if raw is not None:
        grid = pd.read_csv(raw).dropna(subset=["Lon", "Lat", "Prob"])
        sc = ax.scatter(
            grid["Lon"], grid["Lat"], c=grid["Prob"],
            s=7, alpha=.80
        )
        return sc, "Grilla real del proyecto"

    # Interpolación visual reproducible desde las 15 zonas candidatas.
    # Se usa SOLO como fondo explicativo del informe público.
    west, east = -82.0, -76.25
    south, north = -14.1, -5.9
    gx = np.linspace(west, east, 155)
    gy = np.linspace(south, north, 220)
    xx, yy = np.meshgrid(gx, gy)
    field = np.zeros_like(xx, dtype=float)
    weight = np.zeros_like(xx, dtype=float)

    for z in zones.itertuples(index=False):
        d2 = ((xx-z.Lon)/0.55)**2 + ((yy-z.Lat)/0.65)**2
        w = np.exp(-0.5*d2)
        field += w * float(z.Prob)
        weight += w

    field = np.divide(field, np.maximum(weight, 1e-9))
    field = np.clip(field, 0, 1)
    cs = ax.scatter(
        xx.ravel(), yy.ravel(), c=field.ravel(),
        s=7, alpha=.72
    )
    return cs, "Interpolación visual desde zonas candidatas (no grilla cliente completa)"


def draw_reference_exclusions(ax):
    for ref in REFERENCE_EXCLUSIONS:
        circ = Circle(
            (ref["lon"], ref["lat"]),
            ref["radius"],
            fill=False,
            linewidth=1.4,
            linestyle="--",
        )
        ax.add_patch(circ)
        ax.annotate(
            ref["name"],
            (ref["lon"], ref["lat"]),
            xytext=(6, 6),
            textcoords="offset points",
            fontsize=7.5,
        )


def detailed_map(assignments, title, filename, show_agent_ids=True):
    fig, ax = plt.subplots(figsize=(8.8, 10))
    sc, background_label = background_probability(ax)
    plt.colorbar(sc, ax=ax, label="Probabilidad / superficie visual")

    for pname, (lon, lat) in PORTS.items():
        ax.scatter(lon, lat, marker="^", s=135)
        ax.annotate(
            pname, (lon, lat),
            xytext=(5, 5), textcoords="offset points",
            fontsize=9, fontweight="bold"
        )

    ax.scatter(
        zones["Lon"], zones["Lat"],
        s=58, marker="x"
    )
    for r in zones.itertuples(index=False):
        ax.annotate(
            f"Z{int(r.zone_id)}",
            (r.Lon, r.Lat),
            xytext=(4,4),
            textcoords="offset points",
            fontsize=7.5,
        )

    draw_reference_exclusions(ax)

    if assignments is not None:
        for r in assignments.itertuples(index=False):
            z = zone_lookup.loc[int(r.zone_id)]
            plon, plat = PORTS[r.port]
            ax.plot(
                [plon, z.Lon],
                [plat, z.Lat],
                linewidth=.75,
                alpha=.55
            )
            if show_agent_ids:
                mx = (plon + z.Lon)/2
                my = (plat + z.Lat)/2
                ax.annotate(
                    f"A{int(r.agent_id)}",
                    (mx, my),
                    xytext=(2,2),
                    textcoords="offset points",
                    fontsize=6.8,
                )

    ax.set_title(title)
    ax.set_xlabel("Longitud")
    ax.set_ylabel("Latitud")
    ax.grid(alpha=.20)
    ax.set_aspect("equal", adjustable="box")
    ax.text(
        0.01, 0.01,
        background_label + "\nCírculos = exclusiones ilustrativas, no SERNANP oficial.",
        transform=ax.transAxes,
        fontsize=7.5,
        va="bottom",
        bbox=dict(boxstyle="round", alpha=.65)
    )
    save(fig, filename)


# -------------------------------------------------------------------
# 1) Mapas detallados
# -------------------------------------------------------------------
detailed_map(
    None,
    "Probabilidad + puertos + zonas candidatas + exclusiones de referencia",
    "mapa_detallado_probabilidad_puertos_zonas.jpg",
    show_agent_ids=False,
)
detailed_map(greedy, "Mapa detallado de asignación — Greedy", "mapa_detallado_greedy.jpg")
detailed_map(milp, "Mapa detallado de asignación — MILP", "mapa_detallado_milp.jpg")
detailed_map(marl, "Mapa detallado de asignación — MARL", "mapa_detallado_marl.jpg")

# Alias histórico usado por el LaTeX anterior.
detailed_map(
    marl,
    "Asignación espacial MARL — conexiones puerto-zona",
    "mapa_final_modelo.jpg",
)

# -------------------------------------------------------------------
# 2) Comparación de métodos
# -------------------------------------------------------------------
for col, title, ylabel, name in [
    ("mean_prob", "Probabilidad media por método", "Probabilidad media", "probabilidad_metodos.jpg"),
    ("total_nm", "Distancia total por método", "Millas náuticas", "distancia_metodos.jpg"),
    ("total_estimated_reference_fuel_l", "Combustible de referencia por método", "Litros estimados", "combustible_metodos.jpg"),
]:
    fig, ax = plt.subplots(figsize=(7.2,4.3))
    ax.bar(comparison["method"], comparison[col])
    ax.set_title(title)
    ax.set_xlabel("Método")
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=.2)
    save(fig, name)

tmp = comparison.copy()
tmp["costo"] = tmp["total_estimated_reference_fuel_l"] * 5.0
fig, ax = plt.subplots(figsize=(7.2,4.3))
ax.bar(tmp["method"], tmp["costo"])
ax.set_title("Costo referencial de combustible — S/ 5.00/L")
ax.set_xlabel("Método")
ax.set_ylabel("S/ (escenario)")
ax.grid(axis="y", alpha=.2)
save(fig, "costo_combustible_escenario.jpg")

# -------------------------------------------------------------------
# 3) Zonas candidatas
# -------------------------------------------------------------------
top_zones = zones.sort_values("Prob", ascending=False).head(10)
fig, ax = plt.subplots(figsize=(8,4.4))
ax.bar(top_zones["zone_id"].astype(int).astype(str), top_zones["Prob"])
ax.set_title("Top 10 zonas candidatas por probabilidad")
ax.set_xlabel("Zona")
ax.set_ylabel("Probabilidad")
ax.grid(axis="y", alpha=.2)
save(fig, "top10_zonas_probabilidad.jpg")

# -------------------------------------------------------------------
# 4) Ocupación por método
# -------------------------------------------------------------------
all_assign = pd.concat([
    greedy.assign(method="Greedy"),
    milp.assign(method="MILP"),
    marl.assign(method="MARL"),
], ignore_index=True)

occ = (
    all_assign.groupby(["method", "zone_id"], as_index=False)
    .size()
    .rename(columns={"size":"n_barcos"})
)
pivot = occ.pivot(index="zone_id", columns="method", values="n_barcos").fillna(0).sort_index()

fig, ax = plt.subplots(figsize=(9.5,4.6))
x = np.arange(len(pivot))
width = .25
methods = list(pivot.columns)
for i, method in enumerate(methods):
    ax.bar(x+(i-1)*width, pivot[method].values, width=width, label=method)
ax.set_xticks(x, pivot.index.astype(str))
ax.set_title("Ocupación de zonas por método")
ax.set_xlabel("Zona")
ax.set_ylabel("Número de barcos")
ax.grid(axis="y", alpha=.2)
ax.legend()
save(fig, "ocupacion_zonas_por_metodo.jpg")

# -------------------------------------------------------------------
# 5) Diagnóstico MARL por puerto
# -------------------------------------------------------------------
port = (
    marl.groupby("port", as_index=False)
    .agg(
        combustible=("estimated_reference_fuel_l","sum"),
        distancia=("route_nm","sum"),
        probabilidad=("prob","mean"),
    )
)

fig, ax = plt.subplots(figsize=(7.2,4.3))
ax.bar(port["port"], port["combustible"])
ax.set_title("Combustible de referencia por puerto — MARL")
ax.set_ylabel("Litros estimados")
ax.grid(axis="y", alpha=.2)
save(fig, "combustible_puerto_marl.jpg")

fig, ax = plt.subplots(figsize=(7.2,4.3))
ax.bar(port["port"], port["distancia"])
ax.set_title("Distancia total por puerto — MARL")
ax.set_ylabel("Millas náuticas")
ax.grid(axis="y", alpha=.2)
save(fig, "distancia_puerto_marl.jpg")

# -------------------------------------------------------------------
# 6) Diagnóstico MARL por barco
# -------------------------------------------------------------------
marl_sorted = marl.sort_values("agent_id")

fig, ax = plt.subplots(figsize=(9.2,4.4))
ax.bar(marl_sorted["agent_id"].astype(str), marl_sorted["estimated_reference_fuel_l"])
ax.set_title("Combustible estimado por barco — MARL")
ax.set_xlabel("Agente")
ax.set_ylabel("Litros estimados")
ax.grid(axis="y", alpha=.2)
save(fig, "combustible_barco_marl.jpg")

fig, ax = plt.subplots(figsize=(9.2,4.4))
ax.bar(marl_sorted["agent_id"].astype(str), marl_sorted["policy_reward"])
ax.set_title("Recompensa de política por barco — MARL")
ax.set_xlabel("Agente")
ax.set_ylabel("Policy reward")
ax.grid(axis="y", alpha=.2)
save(fig, "policy_reward_barco_marl.jpg")

# Ocupación MARL individual
occ_marl = marl.groupby("zone_id").size().sort_index()
fig, ax = plt.subplots(figsize=(8,4.3))
ax.bar(occ_marl.index.astype(str), occ_marl.values)
ax.set_title("Ocupación de zonas — MARL")
ax.set_xlabel("Zona")
ax.set_ylabel("Número de barcos")
ax.grid(axis="y", alpha=.2)
save(fig, "ocupacion_marl.jpg")

# Trade-off distancia/probabilidad
fig, ax = plt.subplots(figsize=(7,5))
ax.scatter(marl["route_nm"], marl["prob"], s=65)
for r in marl.itertuples(index=False):
    ax.annotate(str(r.agent_id), (r.route_nm, r.prob), xytext=(3,3), textcoords="offset points", fontsize=8)
ax.set_title("Trade-off distancia vs probabilidad — MARL")
ax.set_xlabel("Distancia (NM)")
ax.set_ylabel("Probabilidad")
ax.grid(alpha=.2)
save(fig, "tradeoff_marl.jpg")

# -------------------------------------------------------------------
# 7) Historial de entrenamiento
# -------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.5,4.2))
ax.plot(history["update"], history["simulated_episode_reward"], linewidth=1.0, label="Recompensa")
ax.plot(
    history["update"],
    history["simulated_episode_reward"].rolling(10, min_periods=1).mean(),
    linewidth=2.2,
    label="Media móvil 10"
)
ax.set_title("Historial detallado de entrenamiento MARL")
ax.set_xlabel("Actualización")
ax.set_ylabel("Recompensa simulada")
ax.grid(alpha=.2)
ax.legend()
save(fig, "entrenamiento_marl.jpg")
save(fig, "entrenamiento_marl_detallado.jpg")

# -------------------------------------------------------------------
# 8) Montaje de simulación
# -------------------------------------------------------------------
frames = [0.0, 0.33, 0.66, 1.0]
fig, axes = plt.subplots(2,2,figsize=(10,10), sharex=True, sharey=True)
for ax, frac in zip(axes.flat, frames):
    ax.scatter(zones["Lon"], zones["Lat"], c=zones["Prob"], s=55, alpha=.55)
    for pname,(lon,lat) in PORTS.items():
        ax.scatter(lon, lat, marker="^", s=95)
    for r in marl.itertuples(index=False):
        z = zone_lookup.loc[int(r.zone_id)]
        plon, plat = PORTS[r.port]
        x = plon + frac*(z.Lon-plon)
        y = plat + frac*(z.Lat-plat)
        ax.scatter(x,y,s=28)
        ax.plot([plon,z.Lon],[plat,z.Lat],linewidth=.4,alpha=.2)
    ax.set_title(f"Progreso simulado: {frac*100:.0f}%")
    ax.grid(alpha=.15)
    ax.set_aspect("equal", adjustable="box")
fig.suptitle("Simulación visual del desplazamiento de los 15 agentes", fontsize=14)
save(fig, "simulacion_montaje.jpg")

print("Figuras generadas en:", FIG)
for p in sorted(FIG.glob("*.jpg")):
    print(" -", p.name)
