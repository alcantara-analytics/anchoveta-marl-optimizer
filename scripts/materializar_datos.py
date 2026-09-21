from __future__ import annotations

from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "raw" / "MapProbabilidad_adulto.csv"
EXPECTED_SHA256 = "3eb0abd9308a2bda62285eb9718485c612e137be13fc51c33bcdfbe2fed3704f"


def materializar() -> Path:
    """
    Verifica el dataset versionado del proyecto.

    El pipeline NO genera ni reconstruye una grilla alternativa.
    Si el archivo falta o cambia de manera no documentada, la ejecución se detiene.
    """
    if not DATASET.exists():
        raise FileNotFoundError(
            f"Falta el dataset obligatorio: {DATASET}. "
            "No se usará una grilla demo o sintética."
        )

    digest = hashlib.sha256(DATASET.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA256:
        raise RuntimeError(
            "MapProbabilidad_adulto.csv no coincide con la versión validada. "
            f"Esperado={EXPECTED_SHA256}; obtenido={digest}"
        )

    print(f"Dataset verificado: {DATASET}")
    print(f"SHA256: {digest}")
    return DATASET


if __name__ == "__main__":
    materializar()
