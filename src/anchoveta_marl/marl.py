from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass
class MARLConfig:
    updates: int = 120
    episodes_per_update: int = 12
    lr: float = 0.08
    entropy_coef: float = 0.015
    fuel_weight: float = 0.25
    congestion_weight: float = 0.08
    overflow_penalty: float = 0.50
    max_boats_per_zone: int = 3
    seed: int = 42


def _softmax(x: np.ndarray) -> np.ndarray:
    y = x - np.max(x, axis=-1, keepdims=True)
    e = np.exp(y)
    return e / np.sum(e, axis=-1, keepdims=True)


def _build_agent_scores(
    agents: pd.DataFrame,
    zones: pd.DataFrame,
    costs: pd.DataFrame,
    theta: np.ndarray,
) -> np.ndarray:
    """
    Política compartida simple condicionada por:
    - probabilidad real de cada zona;
    - combustible normalizado puerto-zona;
    - sesgo aprendido por puerto y zona.

    theta tiene forma (3, Z). No se generan mapas sintéticos ni se perturba Prob.
    """
    port_order = ["Malabrigo", "Chimbote", "Callao"]
    port_idx = {p: i for i, p in enumerate(port_order)}
    z = len(zones)

    fuel_scale = max(float(costs["fuel_l"].max()), 1.0)
    prob = zones.sort_values("zone_id")["Prob"].to_numpy(dtype=float)

    scores = np.zeros((len(agents), z), dtype=float)
    for i, a in agents.iterrows():
        sub = (
            costs[costs["port"] == a["port"]]
            .sort_values("zone_id")
        )
        fuel = sub["fuel_l"].to_numpy(dtype=float) / fuel_scale
        scores[i] = (
            2.2 * prob
            - 0.9 * fuel
            + theta[port_idx[a["port"]]]
        )
    return scores


def _reward_for_actions(
    agents: pd.DataFrame,
    zones: pd.DataFrame,
    costs: pd.DataFrame,
    actions: np.ndarray,
    cfg: MARLConfig,
) -> np.ndarray:
    z = len(zones)
    counts = np.bincount(actions, minlength=z)
    fuel_scale = max(float(costs["fuel_l"].max()), 1.0)
    zone_prob = zones.set_index("zone_id")["Prob"]

    rewards = np.zeros(len(agents), dtype=float)
    for i, a in agents.iterrows():
        zone = int(actions[i])
        row = costs[
            (costs["port"] == a["port"]) &
            (costs["zone_id"] == zone)
        ].iloc[0]

        congestion = max(0, counts[zone] - 1)
        overflow = max(0, counts[zone] - cfg.max_boats_per_zone)

        rewards[i] = (
            float(zone_prob.loc[zone])
            - cfg.fuel_weight * (float(row["fuel_l"]) / fuel_scale)
            - cfg.congestion_weight * congestion
            - cfg.overflow_penalty * overflow
        )

    return rewards


def train_marl_static(
    agents: pd.DataFrame,
    zones: pd.DataFrame,
    costs: pd.DataFrame,
    cfg: MARLConfig | None = None,
):
    """
    Entrena una política multiagente cooperativa sobre la grilla REAL y estática.

    No crea ni perturba la superficie de probabilidad. La aleatoriedad corresponde
    únicamente al muestreo de acciones durante el aprendizaje.
    """
    cfg = cfg or MARLConfig()
    rng = np.random.default_rng(cfg.seed)

    port_order = ["Malabrigo", "Chimbote", "Callao"]
    port_idx = {p: i for i, p in enumerate(port_order)}
    z = len(zones)

    # Sesgos de política compartida por puerto. Inicialización cero.
    theta = np.zeros((len(port_order), z), dtype=float)
    baseline = 0.0
    history = []

    for update in range(1, cfg.updates + 1):
        grad = np.zeros_like(theta)
        team_rewards = []
        entropies = []

        for _ in range(cfg.episodes_per_update):
            scores = _build_agent_scores(agents, zones, costs, theta)
            probs = _softmax(scores)

            actions = np.array([
                rng.choice(z, p=probs[i])
                for i in range(len(agents))
            ], dtype=int)

            rewards = _reward_for_actions(
                agents, zones, costs, actions, cfg
            )
            team_reward = float(rewards.sum())
            team_rewards.append(team_reward)

            # Ventaja cooperativa: todos aprenden del retorno total de la flota.
            advantage = team_reward - baseline

            for i, a in agents.iterrows():
                p = probs[i]
                onehot = np.zeros(z)
                onehot[actions[i]] = 1.0

                # Gradiente REINFORCE de softmax con entropía.
                local_grad = advantage * (onehot - p)

                entropy_grad = -(np.log(np.clip(p, 1e-12, 1.0)) + 1.0)
                entropy_grad -= np.dot(entropy_grad, p)
                local_grad += cfg.entropy_coef * entropy_grad * p

                grad[port_idx[a["port"]]] += local_grad
                entropies.append(float(-(p * np.log(np.clip(p, 1e-12, 1.0))).sum()))

        grad /= max(cfg.episodes_per_update, 1)
        grad = np.clip(grad, -5.0, 5.0)
        theta += cfg.lr * grad

        mean_reward = float(np.mean(team_rewards))
        baseline = 0.90 * baseline + 0.10 * mean_reward

        history.append({
            "update": update,
            "team_reward_real_grid": mean_reward,
            "baseline": baseline,
            "mean_entropy": float(np.mean(entropies)),
        })

    return theta, pd.DataFrame(history)


def decode_policy_with_capacity(
    agents: pd.DataFrame,
    zones: pd.DataFrame,
    costs: pd.DataFrame,
    theta: np.ndarray,
    max_boats_per_zone: int = 3,
) -> pd.DataFrame:
    """
    Decodifica la política aprendida respetando capacidad máxima por zona.
    """
    scores = _build_agent_scores(agents, zones, costs, theta)
    occupancy = np.zeros(len(zones), dtype=int)
    rows = []

    # Prioriza primero las decisiones con mayor confianza.
    confidence = scores.max(axis=1) - np.partition(scores, -2, axis=1)[:, -2]
    order = np.argsort(-confidence)

    assigned = {}
    for i in order:
        ranking = np.argsort(-scores[i])
        for z in ranking:
            if occupancy[z] < max_boats_per_zone:
                assigned[int(i)] = int(z)
                occupancy[z] += 1
                break

    cfg = MARLConfig(max_boats_per_zone=max_boats_per_zone)
    actions = np.array([assigned[i] for i in range(len(agents))], dtype=int)
    rewards = _reward_for_actions(agents, zones, costs, actions, cfg)

    for i, a in agents.iterrows():
        z = assigned[int(i)]
        row = costs[
            (costs["port"] == a["port"]) &
            (costs["zone_id"] == z)
        ].iloc[0]

        rows.append({
            "agent_id": int(a["agent_id"]),
            "port": a["port"],
            "zone_id": z,
            "prob": float(row["prob"]),
            "route_nm": float(row["route_nm"]),
            "fuel_l": float(row["fuel_l"]),
            "policy_reward": float(rewards[i]),
        })

    return pd.DataFrame(rows).sort_values("agent_id").reset_index(drop=True)
