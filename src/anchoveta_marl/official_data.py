from __future__ import annotations

import json
from pathlib import Path
import time
import numpy as np
import requests
from shapely.geometry import shape
from shapely.ops import unary_union
from shapely import contains_xy


SERNANP_BASE = "https://geoservicios.sernanp.gob.pe/arcgis/rest/services/sernanp_visor/servicio_descarga/MapServer"


def _get_json(url: str, params: dict, retries: int = 3, timeout: int = 60) -> dict:
    headers = {"User-Agent": "anchoveta-marl-optimizer/1.0 academic"}
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"No se pudo consultar {url}: {last}")


def descargar_capa_sernanp(layer_id: int, bbox: dict, cache_dir: Path, nombre: str):
    """Descarga una capa SERNANP como GeoJSON y devuelve geometrías Shapely."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    out = cache_dir / f"{nombre}.geojson"

    url = f"{SERNANP_BASE}/{layer_id}/query"
    params = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "geometry": f"{bbox['west']},{bbox['south']},{bbox['east']},{bbox['north']}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "outSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "f": "geojson",
    }
    data = _get_json(url, params)
    out.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    geoms = [shape(f["geometry"]) for f in data.get("features", []) if f.get("geometry")]
    return geoms, out


def obtener_exclusiones_sernanp(bbox: dict, cache_dir: Path, modo: str = "auto"):
    """Obtiene ANP Nacional Definitiva y Zonas Reservadas.

    modo:
    - "no": no consulta SERNANP.
    - "auto": intenta; si falla, continúa sin la máscara y registra el motivo.
    - "estricto": si falla, detiene el pipeline.
    """
    if modo == "no":
        return [], {"aplicado": False, "estado": "DESACTIVADO_POR_USUARIO", "fuente": SERNANP_BASE}

    try:
        anp, f1 = descargar_capa_sernanp(1, bbox, cache_dir, "SERNANP_ANP_Nacional")
        zr, f2 = descargar_capa_sernanp(2, bbox, cache_dir, "SERNANP_Zonas_Reservadas")
        geoms = anp + zr
        return geoms, {
            "aplicado": bool(geoms),
            "estado": "DESCARGADO_OFICIAL" if geoms else "SIN_FEATURES_EN_BBOX",
            "fuente": SERNANP_BASE,
            "archivos": [str(f1), str(f2)],
            "n_geometrias": len(geoms),
        }
    except Exception as e:
        if modo == "estricto":
            raise
        return [], {
            "aplicado": False,
            "estado": "FALLO_DESCARGA_CONTINUA_SIN_MASCARA",
            "fuente": SERNANP_BASE,
            "error": str(e),
        }


def mascara_legal_desde_geometrias(raw_grid, geometrias):
    """Crea máscara True=permitido con la misma forma de grilla que GridRouter."""
    lons = np.sort(raw_grid["Lon"].unique())
    lats = np.sort(raw_grid["Lat"].unique())
    mask = np.ones((len(lats), len(lons)), dtype=bool)
    if not geometrias:
        return mask

    union = unary_union(geometrias)
    xx, yy = np.meshgrid(lons, lats)
    dentro = contains_xy(union, xx.ravel(), yy.ravel()).reshape(xx.shape)
    mask[dentro] = False
    return mask
