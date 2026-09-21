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
from anchoveta_marl.data import (
    load_probability_grid,
    select_candidate_zones,
)
from anchoveta_marl.official_data import (
    obtener_exclusiones_sernanp,
    mascara_legal_desde_geometrias,
)
from anchoveta_marl.routing import GridRouter
from anchoveta_marl.optimization import (
    build_agents,
    greedy_assignment,
    milp_assignment,
)
from anchoveta_marl.marl import (
    MARLConfig,
    train_marl_static,
    decode_policy_with_capacity,
)
from anchoveta_marl.reporting import (
    resumen_metodo,
    guardar_mapa_probabilidad_zonas,
    guardar_graficos,
    guardar_reporte_html,
)
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

    # Compatibilidad con los optimizadores actuales:
    # la columna fuel_l representa el combustible total ida+retorno.
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
    out = asignacion.drop(columns=["route_nm", "fuel_l"], errors="ignore").merge(
        base, on=["port", "zone_id"], how="left"
    )
    return out


def costos_por_puerto(asignacion: pd.DataFrame):
    return (
        asignacion.groupby("port", as_index=False)
        .agg(
            barcos=("agent_id", "count"),
            probabilidad_media=("prob", "mean"),
            distancia_total_nm=("distancia_total_nm", "sum"),
            horas_total=("horas_total", "sum"),
            combustible_total_l=("combustible_total_l", "sum"),
            costo_total_pen=("costo_total_pen", "sum"),
        )
    )


def main():
    ap = argparse.ArgumentParser(
        description="Optimizador multiagente de flota anchovetera — versión reproducible en español."
    )
    ap.add_argument("--input", default="data/raw/MapProbabilidad_adulto.csv")
    ap.add_argument("--no-gif", action="store_true", help="No genera la animación GIF")
    ap.add_argument(
        "--sernanp",
        choices=["auto", "estricto", "no"],
        default="auto",
        help="auto=intenta usar SERNANP; estricto=si falla se detiene; no=no lo consulta",
    )
    ap.add_argument(
        "--precio-combustible",
        type=float,
        default=5.0,
        help="Precio de escenario en S/ por litro. No es un precio oficial salvo que el usuario lo sustituya.",
    )
    ap.add_argument(
        "--costo-operativo-hora",
        type=float,
        default=0.0,
        help="Costo operativo adicional de escenario S/ por hora. Default 0 para no inventar tripulación/mantenimiento.",
    )
    args = ap.parse_args()

    outdir = ROOT / "outputs"
    outdir.mkdir(exist_ok=True)
    cache_dir = ROOT / "data" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    cfg = FleetConfig()

    dataset_path = ROOT / args.input
    if not dataset_path.exists():
        from materializar_datos import materializar
        materializar()
    prob, procedencia = load_probability_grid(dataset_path)

    bbox = {
        "west": float(prob["Lon"].min()),
        "east": float(prob["Lon"].max()),
        "south": float(prob["Lat"].min()),
        "north": float(prob["Lat"].max()),
    }

    geoms_sernanp, auditoria_sernanp = obtener_exclusiones_sernanp(
        bbox=bbox,
        cache_dir=cache_dir,
        modo=args.sernanp,
    )

    mascara_legal = mascara_legal_desde_geometrias(prob, geoms_sernanp)
    router = GridRouter(prob, legal_mask=mascara_legal)

    # Selección inicial por probabilidad y posterior validación contra el grafo legal.
    zonas_iniciales = select_candidate_zones(prob, n_zones=35)
    legal_rows = []
    for r in zonas_iniciales.itertuples(index=False):
        try:
            node = router.nearest_node(float(r.Lon), float(r.Lat))
            lon_node = float(router.lons[node[1]])
            lat_node = float(router.lats[node[0]])
            if abs(lon_node - float(r.Lon)) <= 0.11 and abs(lat_node - float(r.Lat)) <= 0.11:
                legal_rows.append((float(r.Lon), float(r.Lat), float(r.Prob)))
        except Exception:
            pass

    zones = pd.DataFrame(legal_rows[:25], columns=["Lon", "Lat", "Prob"])
    zones["zone_id"] = np.arange(len(zones), dtype=int)

    if len(zones) < 10:
        raise RuntimeError(
            f"Solo quedaron {len(zones)} zonas candidatas navegables. "
            "Revisa la grilla o la máscara legal."
        )

    agents = build_agents(PORTS, cfg.boats_per_port)

    zone_nodes = [router.nearest_node(r.Lon, r.Lat) for r in zones.itertuples(index=False)]
    port_nodes = {p: router.nearest_node(lon, lat) for p, (lon, lat) in PORTS.items()}

    cost_rows = []
    path_lookup = {}
    for pname, pnode in port_nodes.items():
        for z in zones.itertuples(index=False):
            path, nm = router.astar(pnode, zone_nodes[int(z.zone_id)])
            if not path:
                continue
            cost_rows.append({
                "port": pname,
                "zone_id": int(z.zone_id),
                "prob": float(z.Prob),
                "route_nm": float(nm),
            })
            path_lookup[(pname, int(z.zone_id))] = router.path_lonlat(path)

    costos = pd.DataFrame(cost_rows)
    expected = len(PORTS) * len(zones)
    if len(costos) != expected:
        raise RuntimeError(
            f"Grafo desconectado: existen {len(costos)}/{expected} rutas puerto-zona."
        )

    costos = enriquecer_costos(
        costos,
        cfg=cfg,
        precio_combustible=args.precio_combustible,
        costo_operativo_hora=args.costo_operativo_hora,
    )

    greedy_base = greedy_assignment(
        agents,
        zones,
        costos[["port", "zone_id", "prob", "route_nm", "fuel_l"]],
        cfg.max_boats_per_zone,
    )
    milp_base = milp_assignment(
        agents,
        zones,
        costos[["port", "zone_id", "prob", "route_nm", "fuel_l"]],
        cfg.max_boats_per_zone,
    )

    greedy = anexar_metricas(greedy_base, costos)
    milp = anexar_metricas(milp_base, costos)

    # MARL: entrenamiento cooperativo estático sobre la MISMA grilla real.
    marl_cfg = MARLConfig(
        updates=120,
        episodes_per_update=12,
        max_boats_per_zone=cfg.max_boats_per_zone,
        seed=42,
    )
    theta_marl, historial_marl = train_marl_static(
        agents,
        zones,
        costos[["port", "zone_id", "prob", "route_nm", "fuel_l"]],
        cfg=marl_cfg,
    )
    marl_base = decode_policy_with_capacity(
        agents,
        zones,
        costos[["port", "zone_id", "prob", "route_nm", "fuel_l"]],
        theta_marl,
        max_boats_per_zone=cfg.max_boats_per_zone,
    )
    marl = anexar_metricas(marl_base, costos)

    routes_greedy = {
        int(r.agent_id): path_lookup[(r.port, int(r.zone_id))]
        for r in greedy.itertuples(index=False)
    }
    routes_milp = {
        int(r.agent_id): path_lookup[(r.port, int(r.zone_id))]
        for r in milp.itertuples(index=False)
    }
    routes_marl = {
        int(r.agent_id): path_lookup[(r.port, int(r.zone_id))]
        for r in marl.itertuples(index=False)
    }

    resumen = pd.DataFrame([
        resumen_metodo("Greedy", greedy),
        resumen_metodo("MILP", milp),
        resumen_metodo("MARL", marl),
    ])

    costos_puerto = costos_por_puerto(milp)

    # Guardar tablas
    zones.to_csv(outdir / "zonas_candidatas.csv", index=False)
    costos.to_csv(outdir / "costos_rutas.csv", index=False)
    greedy.to_csv(outdir / "asignacion_greedy.csv", index=False)
    milp.to_csv(outdir / "asignacion_milp.csv", index=False)
    marl.to_csv(outdir / "asignacion_marl.csv", index=False)
    historial_marl.to_csv(outdir / "historial_entrenamiento_marl.csv", index=False)
    resumen.to_csv(outdir / "resumen_metodos.csv", index=False)
    milp.to_csv(outdir / "costos_por_barco.csv", index=False)
    costos_puerto.to_csv(outdir / "costos_por_puerto.csv", index=False)

    # Gráficos
    guardar_mapa_probabilidad_zonas(
        prob, zones, PORTS, outdir / "mapa_probabilidad_zonas.png"
    )
    save_map(
        prob, PORTS, zones, routes_greedy,
        outdir / "mapa_asignacion_greedy.png",
        "Asignación Greedy de la flota"
    )
    save_map(
        prob, PORTS, zones, routes_milp,
        outdir / "mapa_asignacion_milp.png",
        "Asignación MILP de la flota"
    )
    save_map(
        prob, PORTS, zones, routes_marl,
        outdir / "mapa_asignacion_marl.png",
        "Asignación MARL de la flota — entrenamiento sobre MapProbabilidad_adulto.csv"
    )
    guardar_graficos(greedy, milp, resumen, outdir)

    # Simulación de la política MARL final.
    if not args.no_gif:
        save_animation(
            prob, PORTS, zones, routes_marl,
            outdir / "simulacion_flota_marl.gif",
        )

    auditoria = {
        "procedencia_probabilidad": procedencia,
        "probabilidad_simulada": False,
        "rutas_y_movimiento_simulados": True,
        "metodo_visualizacion_principal": "MARL",
        "n_agentes": int(len(agents)),
        "n_zonas": int(len(zones)),
        "flota_homogenea": True,
        "precio_combustible_pen_l": float(args.precio_combustible),
        "precio_combustible_tipo": "PARAMETRO_ESCENARIO_NO_OFICIAL",
        "costo_operativo_hora_pen": float(args.costo_operativo_hora),
        "costo_operativo_tipo": "PARAMETRO_ESCENARIO",
        "sernanp": auditoria_sernanp,
        "advertencia_captura": (
            "Probabilidad de presencia no equivale a toneladas de captura. "
            "Se requiere CPUE/biomasa/captura condicional para monetizar pesca esperada."
        ),
        "marl_entrenamiento": "ESTATICO_SOBRE_MAP_PROBABILIDAD_ADULTO_SIN_PERTURBAR_PROB",
        "marl_updates": int(marl_cfg.updates),
        "nota": (
            "La probabilidad, selección de zonas y entrenamiento MARL usan MapProbabilidad_adulto.csv. "
            "No se genera ni perturba una superficie sintética de probabilidad. "
            "Las rutas y movimientos son decisiones/simulaciones del modelo."
        ),
    }

    (outdir / "auditoria.json").write_text(
        json.dumps(auditoria, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    guardar_reporte_html(outdir, resumen, costos_puerto, auditoria)

    print("\n=== RESUMEN DE MÉTODOS ===")
    print(resumen.to_string(index=False))
    print("\n=== COSTOS POR PUERTO — MILP ===")
    print(costos_puerto.to_string(index=False))
    print("\n=== AUDITORÍA ===")
    print(json.dumps(auditoria, indent=2, ensure_ascii=False))
    print("\nResultados guardados en:", outdir.resolve())


if __name__ == "__main__":
    main()
