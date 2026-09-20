from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from anchoveta_marl.config import PORTS, FleetConfig
from anchoveta_marl.data import load_probability_grid, make_simulated_probability_grid, select_candidate_zones
from anchoveta_marl.routing import GridRouter
from anchoveta_marl.optimization import build_agents, greedy_assignment, milp_assignment
from anchoveta_marl.simulation import save_map, save_animation


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/raw/MapProbabilidad_adulto.csv")
    ap.add_argument("--demo", action="store_true", help="Use explicitly simulated probability grid")
    ap.add_argument("--no-gif", action="store_true")
    args = ap.parse_args()

    outdir = ROOT / "outputs"
    outdir.mkdir(exist_ok=True)
    cfg = FleetConfig()

    if args.demo:
        prob, provenance = make_simulated_probability_grid()
    else:
        prob, provenance = load_probability_grid(ROOT / args.input)

    zones = select_candidate_zones(prob)
    router = GridRouter(prob)
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
                "fuel_l": float(nm * cfg.fuel_l_per_nm_out),
            })
            path_lookup[(pname, int(z.zone_id))] = router.path_lonlat(path)

    costs = pd.DataFrame(cost_rows)
    expected = len(PORTS) * len(zones)
    if len(costs) != expected:
        raise RuntimeError(f"Routing graph disconnected: {len(costs)}/{expected} port-zone routes available")

    greedy = greedy_assignment(agents, zones, costs, cfg.max_boats_per_zone)
    milp = milp_assignment(agents, zones, costs, cfg.max_boats_per_zone)

    routes = {
        int(r.agent_id): path_lookup[(r.port, int(r.zone_id))]
        for r in milp.itertuples(index=False)
    }

    zones.to_csv(outdir / "zones.csv", index=False)
    costs.to_csv(outdir / "route_costs.csv", index=False)
    greedy.to_csv(outdir / "assignment_greedy.csv", index=False)
    milp.to_csv(outdir / "assignment_milp.csv", index=False)

    title = f"Anchoveta fleet assignment — {provenance}"
    save_map(prob, PORTS, zones, routes, outdir / "map_final.png", title)
    if not args.no_gif:
        save_animation(prob, PORTS, zones, routes, outdir / "simulation.gif")

    audit = {
        "probability_source_type": provenance,
        "simulated_probability": provenance == "SIMULATED_DEMO",
        "simulation_output": True,
        "external_environment_used": False,
        "n_agents": int(len(agents)),
        "n_zones": int(len(zones)),
        "method_for_visualization": "MILP",
        "note": (
            "Vessel movement is a model simulation. When --demo is used, the probability field is also simulated. "
            "When a client CSV is used, probability is client-supplied but routes/movement remain simulated decisions."
        ),
    }
    (outdir / "audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(audit, indent=2, ensure_ascii=False))
    print("Outputs:", outdir.resolve())


if __name__ == "__main__":
    main()
