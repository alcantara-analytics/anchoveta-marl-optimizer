from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

DATASET_NAME = "MapProbabilidad_adulto.csv"


def resolve_probability_grid(path: str | Path | None = None, repo_root: str | Path | None = None) -> Path:
    """Resuelve la ubicación del archivo base del proyecto sin crear datos alternativos."""
    if path is not None:
        p = Path(path)
        if p.exists():
            return p.resolve()
        raise FileNotFoundError(f"No existe el archivo indicado: {p}")

    root = Path(repo_root) if repo_root is not None else Path.cwd()
    candidates = [
        root / DATASET_NAME,
        root / "data" / "raw" / DATASET_NAME,
    ]
    for p in candidates:
        if p.exists():
            return p.resolve()

    raise FileNotFoundError(
        f"No se encontró {DATASET_NAME}. El pipeline no genera una grilla demo ni interpolada."
    )


def load_probability_grid(path: str | Path) -> tuple[pd.DataFrame, str]:
    """Carga exclusivamente MapProbabilidad_adulto.csv."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"No existe {p}")

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
    n_zones: int = 15,
    min_sep_deg: float = 0.25,
) -> pd.DataFrame:
    """Selecciona zonas de alta probabilidad manteniendo separación espacial mínima."""
    selected: list[tuple[float, float, float]] = []

    for r in df.sort_values("Prob", ascending=False).itertuples(index=False):
        candidate = (float(r.Lon), float(r.Lat), float(r.Prob))
        if all(
            (candidate[0] - q[0]) ** 2 + (candidate[1] - q[1]) ** 2 >= min_sep_deg ** 2
            for q in selected
        ):
            selected.append(candidate)
        if len(selected) >= n_zones:
            break

    zones = pd.DataFrame(selected, columns=["Lon", "Lat", "Prob"])
    zones["zone_id"] = np.arange(len(zones), dtype=int)

    if len(zones) < min(5, n_zones):
        raise ValueError("Muy pocas zonas candidatas espacialmente separadas")

    return zones
