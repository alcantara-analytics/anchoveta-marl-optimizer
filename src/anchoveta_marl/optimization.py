from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.sparse import lil_matrix


def build_agents(ports, boats_per_port=5):
    rows = []
    aid = 0
    for port, (lon, lat) in ports.items():
        for _ in range(boats_per_port):
            rows.append({"agent_id": aid, "port": port, "home_lon": lon, "home_lat": lat})
            aid += 1
    return pd.DataFrame(rows)


def greedy_assignment(agents, zones, costs, max_boats_per_zone=3, fuel_weight=0.25):
    fuel_scale = max(float(costs["fuel_l"].max()), 1.0)
    occ = np.zeros(len(zones), dtype=int)
    rows = []
    for a in agents.itertuples(index=False):
        options = costs[costs["port"] == a.port].copy()
        options["occ"] = options["zone_id"].map(lambda z: occ[int(z)])
        options = options[options["occ"] < max_boats_per_zone]
        options["score"] = options["prob"] - fuel_weight*(options["fuel_l"]/fuel_scale) - 0.08*options["occ"]
        best = options.sort_values("score", ascending=False).iloc[0]
        zid = int(best.zone_id)
        occ[zid] += 1
        rows.append({
            "agent_id": int(a.agent_id), "port": a.port, "zone_id": zid,
            "prob": float(best.prob), "route_nm": float(best.route_nm),
            "fuel_l": float(best.fuel_l), "score": float(best.score),
        })
    return pd.DataFrame(rows)


def milp_assignment(agents, zones, costs, max_boats_per_zone=3, fuel_weight=0.25):
    a_n, z_n = len(agents), len(zones)
    fuel_scale = max(float(costs["fuel_l"].max()), 1.0)
    c = np.zeros(a_n*z_n)
    for i, a in agents.iterrows():
        sub = costs[costs["port"] == a["port"]].set_index("zone_id")
        for z in range(z_n):
            value = float(sub.loc[z, "prob"]) - fuel_weight*(float(sub.loc[z, "fuel_l"])/fuel_scale)
            c[i*z_n+z] = -value

    m = lil_matrix((a_n+z_n, a_n*z_n), dtype=float)
    lb, ub = [], []
    for i in range(a_n):
        for z in range(z_n):
            m[i, i*z_n+z] = 1
        lb.append(1.0); ub.append(1.0)
    for z in range(z_n):
        for i in range(a_n):
            m[a_n+z, i*z_n+z] = 1
        lb.append(0.0); ub.append(float(max_boats_per_zone))

    res = milp(
        c=c,
        integrality=np.ones(a_n*z_n),
        bounds=Bounds(np.zeros(a_n*z_n), np.ones(a_n*z_n)),
        constraints=LinearConstraint(m.tocsr(), np.array(lb), np.array(ub)),
        options={"time_limit": 30},
    )
    if not res.success:
        raise RuntimeError(res.message)

    x = res.x.reshape(a_n, z_n)
    rows = []
    for i, a in agents.iterrows():
        z = int(np.argmax(x[i]))
        row = costs[(costs["port"] == a["port"]) & (costs["zone_id"] == z)].iloc[0]
        rows.append({
            "agent_id": int(a.agent_id), "port": a.port, "zone_id": z,
            "prob": float(row.prob), "route_nm": float(row.route_nm), "fuel_l": float(row.fuel_l),
        })
    return pd.DataFrame(rows)
