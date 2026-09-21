from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
OUTPUTS = REPO / "outputs"
FIG = ROOT / "figures"
FIG.mkdir(parents=True, exist_ok=True)

PORTS = {
    "Malabrigo": (-79.44141666666667, -7.692789583333334),
    "Chimbote": (-78.9475, -9.075833333333334),
    "Callao": (-77.14027777777778, -12.045),
}

GRID = pd.read_csv(REPO / "data" / "raw" / "MapProbabilidad_adulto.csv").dropna(subset=["Lon", "Lat", "Prob"])
ZONES = pd.read_csv(OUTPUTS / "zonas_candidatas.csv")
RESUMEN = pd.read_csv(OUTPUTS / "resumen_metodos.csv")
GREEDY = pd.read_csv(OUTPUTS / "asignacion_greedy.csv")
MILP = pd.read_csv(OUTPUTS / "asignacion_milp.csv")
MARL = pd.read_csv(OUTPUTS / "asignacion_marl.csv")
HISTORY = pd.read_csv(OUTPUTS / "historial_entrenamiento_marl.csv")

ZONE_LOOKUP = ZONES.set_index("zone_id")


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIG / name, dpi=190, bbox_inches="tight", format="jpg")
    plt.close(fig)


def probability_background(ax):
    sc = ax.scatter(
        GRID["Lon"], GRID["Lat"], c=GRID["Prob"],
        s=7, alpha=.82, vmin=0, vmax=1
    )
    return sc


def plot_ports_and_zones(ax):
    for pname, (lon, lat) in PORTS.items():
        ax.scatter(lon, lat, marker="^", s=125)
        ax.annotate(
            pname, (lon, lat), xytext=(5, 5), textcoords="offset points",
            fontsize=9, fontweight="bold"
        )

    ax.scatter(ZONES["Lon"], ZONES["Lat"], s=52, marker="x")
    for r in ZONES.itertuples(index=False):
        ax.annotate(
            f"Z{int(r.zone_id)}", (r.Lon, r.Lat),
            xytext=(4,4), textcoords="offset points", fontsize=7.3
        )


def detailed_map(assignments, trajectories, title, filename):
    fig, ax = plt.subplots(figsize=(8.8, 10))
    sc = probability_background(ax)
    plt.colorbar(sc, ax=ax, label="Probabilidad de presencia de anchoveta")
    plot_ports_and_zones(ax)

    if assignments is not None and trajectories is not None:
        for aid, g in trajectories.groupby("agent_id"):
            g = g.sort_values("step")
            ax.plot(g["lon"], g["lat"], linewidth=.8, alpha=.62)
            middle = g.iloc[len(g)//2]
            ax.annotate(
                f"A{int(aid)}", (middle["lon"], middle["lat"]),
                xytext=(2,2), textcoords="offset points", fontsize=6.8
            )

    ax.set_title(title)
    ax.set_xlabel("Longitud")
    ax.set_ylabel("Latitud")
    ax.grid(alpha=.20)
    ax.set_aspect("equal", adjustable="box")
    ax.text(
        0.01, 0.01,
        "Fondo: MapProbabilidad_adulto.csv completo.\n"
        "No se dibujan exclusiones regulatorias si SERNANP no fue aplicado.",
        transform=ax.transAxes, fontsize=7.2, va="bottom",
        bbox=dict(boxstyle="round", alpha=.65)
    )
    save(fig, filename)


TG = pd.read_csv(OUTPUTS / "trayectorias_greedy.csv")
TM = pd.read_csv(OUTPUTS / "trayectorias_milp.csv")
TR = pd.read_csv(OUTPUTS / "trayectorias_marl.csv")

detailed_map(None, None,
             "Probabilidad de anchoveta + puertos + zonas candidatas",
             "mapa_detallado_probabilidad_puertos_zonas.jpg")
detailed_map(GREEDY, TG, "Asignación y rutas A* — Greedy", "mapa_detallado_greedy.jpg")
detailed_map(MILP, TM, "Asignación y rutas A* — MILP", "mapa_detallado_milp.jpg")
detailed_map(MARL, TR, "Asignación y rutas A* — MARL", "mapa_detallado_marl.jpg")
detailed_map(MARL, TR, "Asignación espacial MARL sobre la grilla completa", "mapa_final_modelo.jpg")

# Comparación de métodos
for col, title, ylabel, name in [
    ("probabilidad_media", "Probabilidad media por método", "Probabilidad media", "probabilidad_metodos.jpg"),
    ("distancia_total_nm", "Distancia total por método", "Millas náuticas", "distancia_metodos.jpg"),
    ("combustible_total_l", "Combustible total por método", "Litros estimados", "combustible_metodos.jpg"),
]:
    fig, ax = plt.subplots(figsize=(7.2,4.3))
    ax.bar(RESUMEN["metodo"], RESUMEN[col])
    ax.set_title(title)
    ax.set_xlabel("Método")
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=.2)
    save(fig, name)

tmp = RESUMEN.copy()
tmp["costo_ref"] = tmp["combustible_total_l"] * 5.0
fig, ax = plt.subplots(figsize=(7.2,4.3))
ax.bar(tmp["metodo"], tmp["costo_ref"])
ax.set_title("Costo referencial de combustible — S/ 5.00/L")
ax.set_xlabel("Método")
ax.set_ylabel("S/ (escenario)")
ax.grid(axis="y", alpha=.2)
save(fig, "costo_combustible_escenario.jpg")

top_zones = ZONES.sort_values("Prob", ascending=False).head(10)
fig, ax = plt.subplots(figsize=(8,4.4))
ax.bar(top_zones["zone_id"].astype(int).astype(str), top_zones["Prob"])
ax.set_title("Top 10 zonas candidatas por probabilidad")
ax.set_xlabel("Zona")
ax.set_ylabel("Probabilidad")
ax.grid(axis="y", alpha=.2)
save(fig, "top10_zonas_probabilidad.jpg")

all_assign = pd.concat([
    GREEDY.assign(metodo="Greedy"),
    MILP.assign(metodo="MILP"),
    MARL.assign(metodo="MARL"),
], ignore_index=True)
occ = (
    all_assign.groupby(["metodo", "zone_id"], as_index=False)
    .size().rename(columns={"size":"n_barcos"})
)
pivot = occ.pivot(index="zone_id", columns="metodo", values="n_barcos").fillna(0).sort_index()

fig, ax = plt.subplots(figsize=(9.5,4.6))
x = np.arange(len(pivot))
width = .25
methods = list(pivot.columns)
for i, method in enumerate(methods):
    ax.bar(x+(i-(len(methods)-1)/2)*width, pivot[method].values, width=width, label=method)
ax.set_xticks(x, pivot.index.astype(str))
ax.set_title("Ocupación de zonas por método")
ax.set_xlabel("Zona")
ax.set_ylabel("Número de barcos")
ax.grid(axis="y", alpha=.2)
ax.legend()
save(fig, "ocupacion_zonas_por_metodo.jpg")

port = (
    MARL.groupby("port", as_index=False)
    .agg(
        combustible=("combustible_total_l","sum"),
        distancia=("distancia_total_nm","sum"),
        probabilidad=("prob","mean"),
    )
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

marl_sorted = MARL.sort_values("agent_id")
fig, ax = plt.subplots(figsize=(9.2,4.4))
ax.bar(marl_sorted["agent_id"].astype(str), marl_sorted["combustible_total_l"])
ax.set_title("Combustible total por barco — MARL")
ax.set_xlabel("Agente")
ax.set_ylabel("Litros estimados")
ax.grid(axis="y", alpha=.2)
save(fig, "combustible_barco_marl.jpg")

fig, ax = plt.subplots(figsize=(9.2,4.4))
ax.bar(marl_sorted["agent_id"].astype(str), marl_sorted["policy_reward"])
ax.set_title("Recompensa de política por barco — MARL")
ax.set_xlabel("Agente")
ax.set_ylabel("Reward")
ax.grid(axis="y", alpha=.2)
save(fig, "policy_reward_barco_marl.jpg")

occ_marl = MARL.groupby("zone_id").size().sort_index()
fig, ax = plt.subplots(figsize=(8,4.3))
ax.bar(occ_marl.index.astype(str), occ_marl.values)
ax.set_title("Ocupación de zonas — MARL")
ax.set_xlabel("Zona")
ax.set_ylabel("Número de barcos")
ax.grid(axis="y", alpha=.2)
save(fig, "ocupacion_marl.jpg")

fig, ax = plt.subplots(figsize=(7,5))
ax.scatter(MARL["distancia_total_nm"], MARL["prob"], s=65)
for r in MARL.itertuples(index=False):
    ax.annotate(str(r.agent_id), (r.distancia_total_nm, r.prob), xytext=(3,3), textcoords="offset points", fontsize=8)
ax.set_title("Trade-off distancia vs probabilidad — MARL")
ax.set_xlabel("Distancia total ida + retorno (NM)")
ax.set_ylabel("Probabilidad")
ax.grid(alpha=.2)
save(fig, "tradeoff_marl.jpg")

reward_col = "team_reward_real_grid"
fig, ax = plt.subplots(figsize=(8.5,4.2))
ax.plot(HISTORY["update"], HISTORY[reward_col], linewidth=1.0, label="Reward medio")
ax.plot(
    HISTORY["update"], HISTORY[reward_col].rolling(10, min_periods=1).mean(),
    linewidth=2.2, label="Media móvil 10"
)
ax.set_title("Entrenamiento MARL sobre MapProbabilidad_adulto.csv")
ax.set_xlabel("Actualización")
ax.set_ylabel("Reward de equipo")
ax.grid(alpha=.2)
ax.legend()
fig.tight_layout()
fig.savefig(FIG / "entrenamiento_marl.jpg", dpi=190, bbox_inches="tight", format="jpg")
fig.savefig(FIG / "entrenamiento_marl_detallado.jpg", dpi=190, bbox_inches="tight", format="jpg")
plt.close(fig)

# Montaje de simulación siguiendo rutas A* del resultado MARL
frames = [0.0, 0.33, 0.66, 1.0]
fig, axes = plt.subplots(2,2,figsize=(10,10), sharex=True, sharey=True)
for ax, frac in zip(axes.flat, frames):
    sc = ax.scatter(GRID["Lon"], GRID["Lat"], c=GRID["Prob"], s=5, alpha=.25, vmin=0, vmax=1)
    for pname,(lon,lat) in PORTS.items():
        ax.scatter(lon, lat, marker="^", s=90)

    for aid, g in TR.groupby("agent_id"):
        g = g.sort_values("step").reset_index(drop=True)
        idx = min(int(round(frac * (len(g)-1))), len(g)-1)
        current = g.iloc[idx]
        ax.plot(g["lon"], g["lat"], linewidth=.4, alpha=.18)
        ax.scatter(current["lon"], current["lat"], s=26)

    ax.set_title(f"Progreso de ruta: {frac*100:.0f}%")
    ax.grid(alpha=.12)
    ax.set_aspect("equal", adjustable="box")
fig.suptitle("Simulación de los 15 agentes sobre rutas A* — MARL", fontsize=14)
save(fig, "simulacion_montaje.jpg")

# Tabla LaTeX dinámica para evitar números desactualizados.
table = RESUMEN.copy()
table["costo_ref"] = table["combustible_total_l"] * 5.0
lines = [
    r"\begin{table}[H]",
    r"\centering",
    r"\caption{Resultados generados automáticamente con MapProbabilidad\_adulto.csv.}",
    r"\resizebox{0.98\textwidth}{!}{\begin{tabular}{lrrrrr}",
    r"\toprule",
    r"Método & Prob. media & Distancia total (NM) & Combustible (L) & Zonas & Costo ref. (S/) \\",
    r"\midrule",
]
for r in table.itertuples(index=False):
    lines.append(
        f"{r.metodo} & {r.probabilidad_media:.4f} & {r.distancia_total_nm:,.2f} & "
        f"{r.combustible_total_l:,.2f} & {int(r.zonas_utilizadas)} & {r.costo_ref:,.0f} \\\\"
    )
lines += [r"\bottomrule", r"\end{tabular}}", r"\end{table}"]
(ROOT / "tabla_resultados_generada.tex").write_text("\n".join(lines), encoding="utf-8")

print("Figuras y tabla generadas a partir de outputs/ y MapProbabilidad_adulto.csv.")
