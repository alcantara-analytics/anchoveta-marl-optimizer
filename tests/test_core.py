import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from anchoveta_marl.config import PORTS, FleetConfig
from anchoveta_marl.data import make_simulated_probability_grid, select_candidate_zones
from anchoveta_marl.routing import GridRouter
from anchoveta_marl.optimization import build_agents


def test_demo_data_is_explicitly_simulated():
    df, provenance = make_simulated_probability_grid(seed=1)
    assert provenance == "SIMULATED_DEMO"
    assert not df.empty
    assert df["Prob"].between(0, 1).all()


def test_fleet_has_15_agents():
    cfg = FleetConfig()
    agents = build_agents(PORTS, cfg.boats_per_port)
    assert len(agents) == 15
    assert agents.groupby("port").size().eq(5).all()


def test_router_finds_path_in_demo_grid():
    df, _ = make_simulated_probability_grid(seed=1)
    zones = select_candidate_zones(df, n_zones=8)
    router = GridRouter(df)
    pnode = router.nearest_node(*PORTS["Chimbote"])
    znode = router.nearest_node(float(zones.iloc[0].Lon), float(zones.iloc[0].Lat))
    path, nm = router.astar(pnode, znode)
    assert path
    assert nm >= 0
