import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from anchoveta_marl.config import PORTS, FleetConfig
from anchoveta_marl.data import resolve_probability_grid, load_probability_grid, select_candidate_zones
from anchoveta_marl.routing import GridRouter
from anchoveta_marl.optimization import build_agents


def test_dataset_base_existe_y_se_usa_directamente():
    path = resolve_probability_grid(repo_root=ROOT)
    assert path.name == "MapProbabilidad_adulto.csv"
    df, provenance = load_probability_grid(path)
    assert provenance == "MAP_PROBABILIDAD_ADULTO"
    assert len(df) == 11752
    assert df["Prob"].between(0, 1).all()


def test_fleet_has_15_agents():
    cfg = FleetConfig()
    agents = build_agents(PORTS, cfg.boats_per_port)
    assert len(agents) == 15
    assert agents.groupby("port").size().eq(5).all()


def test_router_finds_path_on_project_grid():
    path = resolve_probability_grid(repo_root=ROOT)
    df, _ = load_probability_grid(path)
    zones = select_candidate_zones(df, n_zones=8)
    router = GridRouter(df)
    pnode = router.nearest_node(*PORTS["Chimbote"])
    znode = router.nearest_node(float(zones.iloc[0].Lon), float(zones.iloc[0].Lat))
    route, nm = router.astar(pnode, znode)
    assert route
    assert nm >= 0
