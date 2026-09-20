from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
FIG = ROOT / "figures"
FIG.mkdir(parents=True, exist_ok=True)

PORTS = {
    "Malabrigo": (-79.44141666666667, -7.692789583333334),
    "Chimbote": (-78.9475, -9.075833333333334),
    "Callao": (-77.14027777777778, -12.045),
}

comparison = pd.read_csv(DATA / "comparison.csv")
greedy = pd.read_csv(DATA / "greedy.csv")
milp = pd.read_csv(DATA / "milp.csv")
marl = pd.read_csv(DATA / "marl_assignment.csv")
zones = pd.read_csv(DATA / "zones.csv")
history = pd.read_csv(DATA / "training_history.csv")

def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIG / name, dpi=180, bbox_inches="tight", format="jpg")
    plt.close(fig)

# 1) Mapa de asignación MARL basado en resultados derivados.
fig, ax = plt.subplots(figsize=(8.8, 8.5))
sc = ax.scatter(zones["Lon"], zones["Lat"], c=zones["Prob"], s=150, edgecolor="black", linewidth=.5)
plt.colorbar(sc, ax=ax, label="Probabilidad")
for r in zones.itertuples(index=False):
    ax.annotate(f"Z{int(r.zone_id)}", (r.Lon, r.Lat), xytext=(4,4), textcoords="offset points", fontsize=8)

zone_lookup = zones.set_index("zone_id")
for pname, (lon, lat) in PORTS.items():
    ax.scatter(lon, lat, marker="^", s=160)
    ax.annotate(pname, (lon, lat), xytext=(6,6), textcoords="offset points", fontweight="bold")

for r in marl.itertuples(index=False):
    z = zone_lookup.loc[int(r.zone_id)]
    plon, plat = PORTS[r.port]
    ax.plot([plon, z.Lon], [plat, z.Lat], linewidth=.75, alpha=.45)

ax.set_title("Asignación espacial MARL — conexiones puerto-zona")
ax.set_xlabel("Longitud")
ax.set_ylabel("Latitud")
ax.grid(alpha=.2)
ax.set_aspect("equal", adjustable="box")
save(fig, "mapa_final_modelo.jpg")

# 2) Comparaciones
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

# 3) Costo ilustrativo a S/ 5/L.
tmp = comparison.copy()
tmp["costo"] = tmp["total_estimated_reference_fuel_l"] * 5.0
fig, ax = plt.subplots(figsize=(7.2,4.3))
ax.bar(tmp["method"], tmp["costo"])
ax.set_title("Costo referencial de combustible — S/ 5.00/L")
ax.set_xlabel("Método")
ax.set_ylabel("S/ (escenario)")
ax.grid(axis="y", alpha=.2)
save(fig, "costo_combustible_escenario.jpg")

# 4) Diagnósticos MARL.
port = (
    marl.groupby("port", as_index=False)
    .agg(combustible=("estimated_reference_fuel_l","sum"))
)
fig, ax = plt.subplots(figsize=(7.2,4.3))
ax.bar(port["port"], port["combustible"])
ax.set_title("Combustible de referencia por puerto — MARL")
ax.set_ylabel("Litros estimados")
ax.grid(axis="y", alpha=.2)
save(fig, "combustible_puerto_marl.jpg")

occ = marl.groupby("zone_id").size().sort_index()
fig, ax = plt.subplots(figsize=(8,4.3))
ax.bar(occ.index.astype(str), occ.values)
ax.set_title("Ocupación de zonas — MARL")
ax.set_xlabel("Zona")
ax.set_ylabel("Número de barcos")
ax.grid(axis="y", alpha=.2)
save(fig, "ocupacion_marl.jpg")

fig, ax = plt.subplots(figsize=(7,5))
ax.scatter(marl["route_nm"], marl["prob"], s=65)
for r in marl.itertuples(index=False):
    ax.annotate(str(r.agent_id), (r.route_nm, r.prob), xytext=(3,3), textcoords="offset points", fontsize=8)
ax.set_title("Trade-off distancia vs probabilidad — MARL")
ax.set_xlabel("Distancia (NM)")
ax.set_ylabel("Probabilidad")
ax.grid(alpha=.2)
save(fig, "tradeoff_marl.jpg")

# 5) Historial de entrenamiento.
fig, ax = plt.subplots(figsize=(8.5,4.2))
ax.plot(history["update"], history["simulated_episode_reward"], linewidth=1.2)
ax.plot(
    history["update"],
    history["simulated_episode_reward"].rolling(10, min_periods=1).mean(),
    linewidth=2.2,
    label="Media móvil 10"
)
ax.set_title("Historial de entrenamiento MARL")
ax.set_xlabel("Actualización")
ax.set_ylabel("Recompensa simulada")
ax.grid(alpha=.2)
ax.legend()
save(fig, "entrenamiento_marl.jpg")

# 6) Montaje de simulación: cuatro momentos de desplazamiento lineal
# entre puerto y zona asignada. Es una visualización simulada del plan.
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
