from __future__ import annotations

from pathlib import Path
import base64
import hashlib
import lzma

ROOT = Path(__file__).resolve().parents[1]
ENCODED = ROOT / "data" / "raw" / "MapProbabilidad_adulto.csv.xz.b64"
OUTPUT = ROOT / "data" / "raw" / "MapProbabilidad_adulto.csv"
EXPECTED_SHA256 = "3eb0abd9308a2bda62285eb9718485c612e137be13fc51c33bcdfbe2fed3704f"


def materializar(force: bool = False) -> Path:
    if OUTPUT.exists() and not force:
        digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
        if digest == EXPECTED_SHA256:
            print(f"Dataset ya materializado y verificado: {OUTPUT}")
            return OUTPUT
        raise RuntimeError(
            f"Existe {OUTPUT}, pero su SHA256 no coincide. "
            f"Esperado={EXPECTED_SHA256}, obtenido={digest}"
        )

    if not ENCODED.exists():
        raise FileNotFoundError(
            f"No existe el dataset comprimido versionado: {ENCODED}"
        )

    payload = "".join(ENCODED.read_text(encoding="utf-8").split())
    compressed = base64.b64decode(payload)
    raw = lzma.decompress(compressed)

    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_SHA256:
        raise RuntimeError(
            f"Integridad inválida al materializar dataset. "
            f"Esperado={EXPECTED_SHA256}, obtenido={digest}"
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(raw)
    print(f"Dataset materializado: {OUTPUT}")
    print(f"SHA256: {digest}")
    return OUTPUT


if __name__ == "__main__":
    materializar()
