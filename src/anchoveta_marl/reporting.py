from __future__ import annotations

from pathlib import Path
import html
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def resumen_metodo(nombre: str, asignacion: pd.DataFrame) -> dict:
    return {
        "metodo": nombre,
        "barcos_asignados": int(len(asignacion)),
        "probabilidad_media": float(asignacion["prob"].mean()),
        "distancia_total_nm": float(asignacion["distancia_total_nm"].sum()),
        "combustible_total_l": float(asignacion["combustible_total_l"].sum()),
        "costo_total_pen": float(asignacion["costo_total_pen"].sum()),
        "zonas_utilizadas": int(asignacion["zone_id"].nunique()),
        "ocupacion_maxima_zona": int(asignacion.groupby("zone_id").size().max()),
    }


def guardar_mapa_probabilidad_zonas(prob, zones, ports, out_path):
    fig, ax = plt.subplots(figsize=(9, 10))
    sc = ax.scatter(prob["Lon"], prob["Lat"], c=prob["Prob"], s=8, alpha=.65)
    plt.colorbar(sc, ax=ax, label="Probabilidad de presencia")
    ax.scatter(zones["Lon"], zones["Lat"], marker="x", s=55, label="Zonas candidatas")
    for name, (x, y) in ports.items():
        ax.scatter(x, y, marker="^", s=110)
        ax.annotate(name, (x,y), xytext=(5,5), textcoords="offset points")
    ax.set_title("Mapa de probabilidad y zonas candidatas")
    ax.set_xlabel("Longitud")
    ax.set_ylabel("Latitud")
    ax.grid(alpha=.2)
    ax.set_aspect("equal", adjustable="box")
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def guardar_graficos(asig_greedy, asig_milp, resumen, outdir: Path):
    # Comparación métodos
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(resumen))
    ax.bar(x - .2, resumen["distancia_total_nm"], width=.4, label="Distancia total (NM)")
    ax2 = ax.twinx()
    ax2.bar(x + .2, resumen["probabilidad_media"], width=.4, alpha=.55, label="Probabilidad media")
    ax.set_xticks(x, resumen["metodo"])
    ax.set_ylabel("Distancia total (NM)")
    ax2.set_ylabel("Probabilidad media")
    ax.set_title("Comparación global de métodos")
    ax.grid(axis="y", alpha=.2)
    fig.tight_layout()
    fig.savefig(outdir / "grafico_comparacion_metodos.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    # Costos por barco (MILP)
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.bar(asig_milp["agent_id"].astype(str), asig_milp["costo_total_pen"])
    ax.set_title("Costo total por embarcación — MILP")
    ax.set_xlabel("Agente")
    ax.set_ylabel("Costo de escenario (S/)")
    ax.grid(axis="y", alpha=.2)
    fig.tight_layout()
    fig.savefig(outdir / "grafico_costos_por_barco.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    # Combustible por puerto
    port = asig_milp.groupby("port", as_index=False)["combustible_total_l"].sum()
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(port["port"], port["combustible_total_l"])
    ax.set_title("Combustible total por puerto — MILP")
    ax.set_xlabel("Puerto")
    ax.set_ylabel("Litros")
    ax.grid(axis="y", alpha=.2)
    fig.tight_layout()
    fig.savefig(outdir / "grafico_combustible_por_puerto.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    # Ocupación zonas
    occ = asig_milp.groupby("zone_id").size().sort_index()
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(occ.index.astype(str), occ.values)
    ax.set_title("Ocupación de zonas — MILP")
    ax.set_xlabel("Zona")
    ax.set_ylabel("Número de barcos")
    ax.grid(axis="y", alpha=.2)
    fig.tight_layout()
    fig.savefig(outdir / "grafico_ocupacion_zonas.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    # Trade-off
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(asig_milp["distancia_total_nm"], asig_milp["prob"], s=55)
    for r in asig_milp.itertuples(index=False):
        ax.annotate(str(r.agent_id), (r.distancia_total_nm, r.prob), xytext=(3,3), textcoords="offset points", fontsize=8)
    ax.set_title("Trade-off distancia vs probabilidad — MILP")
    ax.set_xlabel("Distancia total ida + retorno (NM)")
    ax.set_ylabel("Probabilidad de la zona asignada")
    ax.grid(alpha=.2)
    fig.tight_layout()
    fig.savefig(outdir / "grafico_distancia_vs_probabilidad.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def guardar_reporte_html(outdir: Path, resumen: pd.DataFrame, costos_puerto: pd.DataFrame, auditoria: dict):
    imgs = [
        "mapa_probabilidad_zonas.png",
        "mapa_asignacion_greedy.png",
        "mapa_asignacion_milp.png",
        "grafico_comparacion_metodos.png",
        "grafico_costos_por_barco.png",
        "grafico_combustible_por_puerto.png",
        "grafico_ocupacion_zonas.png",
        "grafico_distancia_vs_probabilidad.png",
    ]
    cards = "".join(
        f'<figure><img src="{html.escape(i)}" style="max-width:100%;border:1px solid #ddd"><figcaption>{html.escape(i)}</figcaption></figure>'
        for i in imgs
    )
    doc = f"""<!doctype html><html lang="es"><meta charset="utf-8">
    <title>Reporte Anchoveta MARL Optimizer</title>
    <style>body{{font-family:Arial,sans-serif;max-width:1100px;margin:30px auto;padding:0 18px;color:#17202a}}
    table{{border-collapse:collapse;width:100%;margin:14px 0}}th,td{{border:1px solid #ddd;padding:7px;text-align:right}}th:first-child,td:first-child{{text-align:left}}
    figure{{margin:28px 0}}code{{background:#f3f4f6;padding:2px 5px}}</style>
    <h1>Reporte de resultados — Flota anchovetera</h1>
    <p><b>Advertencia:</b> las rutas y movimientos de embarcaciones son resultados simulados del modelo. La procedencia de la probabilidad y de las restricciones legales se registra en la auditoría.</p>
    <h2>Comparación de métodos</h2>{resumen.to_html(index=False, float_format=lambda x: f"{x:,.3f}")}
    <h2>Costos por puerto — MILP</h2>{costos_puerto.to_html(index=False, float_format=lambda x: f"{x:,.2f}")}
    <h2>Auditoría</h2><pre>{html.escape(str(auditoria))}</pre>
    <h2>Gráficos</h2>{cards}
    </html>"""
    (outdir / "reporte_resultados.html").write_text(doc, encoding="utf-8")
