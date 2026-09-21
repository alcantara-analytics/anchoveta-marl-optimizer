from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from anchoveta_marl.config import PORTS, FleetConfig
from anchoveta_marl.data import resolve_probability_grid, load_probability_grid, select_candidate_zones
from anchoveta_marl.official_data import obtener_exclusiones_sernanp, mascara_legal_desde_geometrias
from anchoveta_marl.routing import GridRouter
from anchoveta_marl.optimization import build_agents, greedy_assignment, milp_assignment
from anchoveta_marl.marl import MARLConfig, train_marl_static, decode_policy_with_capacity
from anchoveta_marl.reporting import resumen_metodo, guardar_mapa_probabilidad_zonas, guardar_graficos, guardar_reporte_html
from anchoveta_marl.simulation import save_map, save_animation


def enriquecer_costos(costos: pd.DataFrame, cfg: FleetConfig, precio_combustible: float, costo_operativo_hora: float):
    x = costos.copy()
    x["distancia_salida_nm"] = x["route_nm"]
    x["distancia_retorno_nm"] = x["route_nm"]
    x["distancia_total_nm"] = x["distancia_salida_nm"] + x["distancia_retorno_nm"]
    x["horas_salida"] = x["distancia_salida_nm"] / cfg.speed_out_kn
    x["horas_retorno"] = x["distancia_retorno_nm"] / cfg.speed_return_kn
    x["horas_total"] = x["horas_salida"] + x["horas_retorno"]
    x["combustible_salida_l"] = x["horas_salida"] * cfg.reference_fuel_lph
    x["combustible_retorno_l"] = x["horas_retorno"] * cfg.reference_fuel_lph
    x["combustible_total_l"] = x["combustible_salida_l"] + x["combustible_retorno_l"]
    x["costo_combustible_pen"] = x["combustible_total_l"] * precio_combustible
    x["costo_operativo_pen"] = x["horas_total"] * costo_operativo_hora
    x["costo_total_pen"] = x["costo_combustible_pen"] + x["costo_operativo_pen"]
    x["fuel_l"] = x["combustible_total_l"]
    return x


def anexar_metricas(asignacion: pd.DataFrame, costos: pd.DataFrame):
    cols = [
        "port", "zone_id",
        "distancia_salida_nm", "distancia_retorno_nm", "distancia_total_nm",
        "horas_salida", "horas_retorno", "horas_total",
        "combustible_salida_l", "combustible_retorno_l", "combustible_total_l",
        "costo_combustible_pen", "costo_operativo_pen", "costo_total_pen",
    ]
    base = costos[cols].drop_duplicates(["port", "zone_id"])
    return asignacion.drop(columns=["route_nm", "fuel_l"], errors="ignore").merge(
        base, on=["port", "zone_id"], how="left"
    )


def resumen_por_puerto(asignaciones: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for metodo, df in asignaciones.items():
        g = (
            df.groupby("port", as_index=False)
            .agg(
                barcos=("agent_id", "count"),
                probabilidad_media=("prob", "mean"),
                distancia_total_nm=("distancia_total_nm", "sum"),
                horas_total=("horas_total", "sum"),
                combustible_total_l=("combustible_total_l", "sum"),
                costo_total_pen=("costo_total_pen", "sum"),
            )
        )
        g.insert(0, "metodo", metodo)
        rows.append(g)
    return pd.concat(rows, ignore_index=True)


def exportar_trayectorias(asignacion: pd.DataFrame, path_lookup: dict, out_path: Path):
    rows = []
    for r in asignacion.itertuples(index=False):
        coords = path_lookup[(r.port, int(r.zone_id))]
        for step, (lon, lat) in enumerate(coords):
            rows.append({
                "agent_id": int(r.agent_id),
                "port": r.port,
                "zone_id": int(r.zone_id),
                "step": step,
                "lon": float(lon),
                "lat": float(lat),
            })
    pd.DataFrame(rows).to_csv(out_path, index=False)


def main():
    ap = argparse.ArgumentParser(
        description="Optimizador de flota anchovetera basado exclusivamente en MapProbabilidad_adulto.csv"
    )
    ap.add_argument("--input", default=None, help="Ruta opcional al CSV. Por defecto usa MapProbabilidad_adulto.csv del repositorio.")
    ap.add_argument("--no-gif", action="store_true")
    ap.add_argument("--sernanp", choices=["auto", "estricto", "no"], default="auto")
    ap.add_argument("--precio-combustible", type=float, default=5.0)
    ap.add_argument("--costo-operativo-hora", type=float, default=0.0)
    ap.add_argument("--n-zonas", type=int, default=15)
    args = ap.parse_args()

    outdir = ROOT / "outputs"
    outdir.mkdir(exist_ok=True)
    cache_dir = ROOT / "data" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    cfg = FleetConfig()

    dataset_path = resolve_probability_grid(args.input, repo_root=ROOT)
    prob, procedencia = load_probability_grid(dataset_path)

    bbox = {
        "west": float(prob["Lon"].min()),
        "east": float(prob["Lon"].max()),
        "south": float(prob["Lat"].min()),
        "north": float(prob["Lat"].max()),
    }

    geoms_sernanp, auditoria_sernanp = obtener_exclusiones_sernanp(
        bbox=bbox, cache_dir=cache_dir, modo=args.sernanp
    )
    mascara_legal = mascara_legal_desde_geometrias(prob, geoms_sernanp)
    router = GridRouter(prob, legal_mask=mascara_legal)

    zonas_iniciales = select_candidate_zones(prob, n_zones=max(args.n_zonas, 15))
    legal_rows = []
    for r in zonas_iniciales.itertuples(index=False):
        node = router.nearest_node(float(r.Lon), float(r.Lat))
        lon_node = float(router.lons[node[1]])
        lat_node = float(router.lats[node[0]])
        if abs(lon_node - float(r.Lon)) <= 0.11 and abs(lat_node - float(r.Lat)) <= 0.11:
            legal_rows.append((float(r.Lon), float(r.Lat), float(r.Prob)))
        if len(legal_rows) >= args.n_zonas:
            break

    zones = pd.DataFrame(legal_rows, columns=["Lon", "Lat", "Prob"])
    zones["zone_id"] = np.arange(len(zones), dtype=int)
    if len(zones) < 5:
        raise RuntimeError("No quedaron suficientes zonas candidatas navegables.")

    agents = build_agents(PORTS, cfg.boats_per_port)
    zone_nodes = [router.nearest_node(r.Lon, r.Lat) for r in zones.itertuples(index=False)]
    port_nodes = {p: router.nearest_node(lon, lat) for p, (lon, lat) in PORTS.items()}

    cost_rows = []
    path_lookup = {}
    for pname, pnode in port_nodes.items():
        for z in zones.itertuples(index=False):
            path, nm = router.astar(pnode, zone_nodes[int(z.zone_id)])
            if not path:
                raise RuntimeError(f"No existe ruta A* segura entre {pname} y zona {z.zone_id}.")
            cost_rows.append({
                "port": pname,
                "zone_id": int(z.zone_id),
                "prob": float(z.Prob),
                "route_nm": float(nm),
            })
            path_lookup[(pname, int(z.zone_id))] = router.path_lonlat(path)

    costos = enriquecer_costos(
        pd.DataFrame(cost_rows), cfg, args.precio_combustible, args.costo_operativo_hora
    )

    base_cols = ["port", "zone_id", "prob", "route_nm", "fuel_l"]
    greedy_base = greedy_assignment(agents, zones, costos[base_cols], cfg.max_boats_per_zone)
    milp_base = milp_assignment(agents, zones, costos[base_cols], cfg.max_boats_per_zone)

    marl_cfg = MARLConfig(
        updates=120,
        episodes_per_update=12,
        max_boats_per_zone=cfg.max_boats_per_zone,
        seed=42,
    )
    theta_marl, historial_marl = train_marl_static(
        agents, zones, costos[base_cols], cfg=marl_cfg
    )
    marl_base = decode_policy_with_capacity(
        agents, zones, costos[base_cols], theta_marl, cfg.max_boats_per_zone
    )

    greedy = anexar_metricas(greedy_base, costos)
    milp = anexar_metricas(milp_base, costos)
    marl = anexar_metricas(marl_base, costos)

    asignaciones = {"Greedy": greedy, "MILP": milp, "MARL": marl}
    rutas = {
        "Greedy": {int(r.agent_id): path_lookup[(r.port, int(r.zone_id))] for r in greedy.itertuples(index=False)},
        "MILP": {int(r.agent_id): path_lookup[(r.port, int(r.zone_id))] for r in milp.itertuples(index=False)},
        "MARL": {int(r.agent_id): path_lookup[(r.port, int(r.zone_id))] for r in marl.itertuples(index=False)},
    }

    resumen = pd.DataFrame([resumen_metodo(k, v) for k, v in asignaciones.items()])
    puertos = resumen_por_puerto(asignaciones)

    zones.to_csv(outdir / "zonas_candidatas.csv", index=False)
    costos.to_csv(outdir / "costos_rutas.csv", index=False)
    greedy.to_csv(outdir / "asignacion_greedy.csv", index=False)
    milp.to_csv(outdir / "asignacion_milp.csv", index=False)
    marl.to_csv(outdir / "asignacion_marl.csv", index=False)
    historial_marl.to_csv(outdir / "historial_entrenamiento_marl.csv", index=False)
    resumen.to_csv(outdir / "resumen_metodos.csv", index=False)
    puertos.to_csv(outdir / "resumen_puerto_metodo.csv", index=False)

    for metodo, df in asignaciones.items():
        nombre = metodo.lower()
        exportar_trayectorias(df, path_lookup, outdir / f"trayectorias_{nombre}.csv")
        df.to_csv(outdir / f"costos_por_barco_{nombre}.csv", index=False)

    guardar_mapa_probabilidad_zonas(prob, zones, PORTS, outdir / "mapa_probabilidad_zonas.png")
    for metodo, df in asignaciones.items():
        save_map(
            prob, PORTS, zones, rutas[metodo],
            outdir / f"mapa_asignacion_{metodo.lower()}.png",
            f"Asignación {metodo} sobre MapProbabilidad_adulto.csv"
        )

    guardar_graficos(greedy, milp, resumen, outdir)

    if not args.no_gif:
        save_animation(prob, PORTS, zones, rutas["MARL"], outdir / "simulacion_flota_marl.gif")

    auditoria = {
        "dataset": str(dataset_path.relative_to(ROOT)) if dataset_path.is_relative_to(ROOT) else str(dataset_path),
        "procedencia_probabilidad": procedencia,
        "grilla_probabilidad_generada_por_pipeline": False,
        "interpolacion_probabilidad_usada": False,
        "n_filas_validas_probabilidad": int(len(prob)),
        "n_agentes": int(len(agents)),
        "n_zonas": int(len(zones)),
        "flota_homogenea": True,
        "marl_entrenamiento": "ESTATICO_SOBRE_MAP_PROBABILIDAD_ADULTO",
        "marl_perturbacion_probabilidad": False,
        "rutas_y_movimiento": "SIMULACION_DE_DECISION_DEL_MODELO_SOBRE_GRILLA_BASE",
        "precio_combustible_pen_l": float(args.precio_combustible),
        "precio_combustible_tipo": "PARAMETRO_DE_ESCENARIO",
        "costo_operativo_hora_pen": float(args.costo_operativo_hora),
        "sernanp": auditoria_sernanp,
        "nota": (
            "Toda la superficie espacial, selección de zonas y optimización usan directamente "
            "MapProbabilidad_adulto.csv. No existe modo demo ni superficie suavizada de reemplazo."
        ),
    }
    (outdir / "auditoria.json").write_text(
        json.dumps(auditoria, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    guardar_reporte_html(outdir, resumen, puertos, auditoria)

    print("\n=== RESUMEN DE MÉTODOS ===")
    print(resumen.to_string(index=False))
    print("\n=== AUDITORÍA ===")
    print(json.dumps(auditoria, indent=2, ensure_ascii=False))
    print("\nResultados:", outdir.resolve())


if __name__ == "__main__":
    main()
