from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd


def load_probability_grid(path: str | Path) -> tuple[pd.DataFrame, str]:
    """Load client probability grid. Returns data and provenance label."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)
    df = pd.read_csv(p)
    required = {"Lon", "Lat", "Prob"}
    if not required.issubset(df.columns):
        raise ValueError(f"Expected columns {required}; got {list(df.columns)}")
    out = df[["Lon", "Lat", "Prob"]].copy()
    out["Lon"] = pd.to_numeric(out["Lon"], errors="coerce")
    out["Lat"] = pd.to_numeric(out["Lat"], errors="coerce")
    out["Prob"] = pd.to_numeric(out["Prob"], errors="coerce")
    out = out.dropna(subset=["Lon", "Lat", "Prob"])
    out = out[out["Prob"].between(0, 1)].reset_index(drop=True)
    if out.empty:
        raise ValueError("Probability grid contains no valid cells")
    return out, "CLIENT_INPUT"


def make_simulated_probability_grid(seed: int = 42) -> tuple[pd.DataFrame, str]:
    """Create an explicit SIMULATED demo grid for CI/testing only."""
    rng = np.random.default_rng(seed)
    lons = np.arange(-81.5, -76.4, 0.10)
    lats = np.arange(-13.5, -6.4, 0.10)
    xx, yy = np.meshgrid(lons, lats)

    def blob(cx, cy, sx, sy, amp):
        return amp * np.exp(-(((xx-cx)/sx)**2 + ((yy-cy)/sy)**2) / 2)

    field = (
        blob(-79.7, -8.1, 0.65, 0.75, 0.95)
        + blob(-78.8, -9.6, 0.55, 0.65, 0.85)
        + blob(-77.6, -12.0, 0.50, 0.70, 0.75)
        + rng.normal(0, 0.025, size=xx.shape)
    )
    field = np.clip(field, 0, 1)
    mask = xx < (-76.7 - 0.05 * (yy + 10))
    field = np.where(mask, field, np.nan)
    df = pd.DataFrame({"Lon": xx.ravel(), "Lat": yy.ravel(), "Prob": field.ravel()})
    df = df.dropna(subset=["Prob"]).reset_index(drop=True)
    return df, "SIMULATED_DEMO"


def select_candidate_zones(df: pd.DataFrame, n_zones: int = 25, min_sep_deg: float = 0.25) -> pd.DataFrame:
    selected: list[tuple[float, float, float]] = []
    for r in df.sort_values("Prob", ascending=False).itertuples(index=False):
        candidate = (float(r.Lon), float(r.Lat), float(r.Prob))
        if all((candidate[0]-q[0])**2 + (candidate[1]-q[1])**2 >= min_sep_deg**2 for q in selected):
            selected.append(candidate)
        if len(selected) >= n_zones:
            break
    zones = pd.DataFrame(selected, columns=["Lon", "Lat", "Prob"])
    zones["zone_id"] = np.arange(len(zones), dtype=int)
    if len(zones) < 5:
        raise ValueError("Too few spatially separated candidate zones")
    return zones
