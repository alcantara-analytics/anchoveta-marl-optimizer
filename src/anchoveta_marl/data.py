from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd


def load_probability_grid(path: str | Path) -> tuple[pd.DataFrame, str]:
    """Carga la grilla MapProbabilidad_adulto.csv usada por todo el proyecto."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"No existe {p}. Ejecuta primero: python scripts/materializar_datos.py"
        )

    df = pd.read_csv(p)
    required = {"Lon", "Lat", "Prob"}
    if not required.issubset(df.columns):
        raise ValueError(f"Se esperaban columnas {required}; se recibió {list(df.columns)}")

    out = df[["Lon", "Lat", "Prob"]].copy()
    out["Lon"] = pd.to_numeric(out["Lon"], errors="coerce")
    out["Lat"] = pd.to_numeric(out["Lat"], errors="coerce")
    out["Prob"] = pd.to_numeric(out["Prob"], errors="coerce")
    out = out.dropna(subset=["Lon", "Lat", "Prob"])
    out = out[out["Prob"].between(0, 1)].reset_index(drop=True)

    if out.empty:
        raise ValueError("MapProbabilidad_adulto.csv no contiene celdas válidas")

    return out, "MAP_PROBABILIDAD_ADULTO"


def select_candidate_zones(
    df: pd.DataFrame,
    n_zones: int = 25,
    min_sep_deg: float = 0.25,
) -> pd.DataFrame:
    """Selecciona zonas de alta probabilidad con separación espacial mínima."""
    selected: list[tuple[float, float, float]] = []

    for r in df.sort_values("Prob", ascending=False).itertuples(index=False):
        candidate = (float(r.Lon), float(r.Lat), float(r.Prob))
        if all(
            (candidate[0]-q[0])**2 + (candidate[1]-q[1])**2 >= min_sep_deg**2
            for q in selected
        ):
            selected.append(candidate)

        if len(selected) >= n_zones:
            break

    zones = pd.DataFrame(selected, columns=["Lon", "Lat", "Prob"])
    zones["zone_id"] = np.arange(len(zones), dtype=int)

    if len(zones) < 5:
        raise ValueError("Muy pocas zonas candidatas espacialmente separadas")

    return zones
