"""Límites del Marco Geoestadístico Nacional (DANE, MGN 2024) desde el servicio ArcGIS REST, como GeoJSON."""

from __future__ import annotations

import json
from pathlib import Path

import requests

from iif import config
from iif.acquire.manifest import PullRecord, append_record, latest_record, make_pull_id, now_iso, sha256_of

TIMEOUT = 300
# El MapServer del mismo servicio responde a `query` con geometría nula en todos los rasgos (B-024);
# el FeatureServer devuelve los polígonos. Misma numeración de capas: 317 Municipio, 319 Departamento.
SERVICE = "https://portalgis.dane.gov.co/mparcgis/rest/services/MGN2024/Serv_CapasMGN_2024/FeatureServer"


def fetch_layer(
    source: dict,
    *,
    out_path: Path | None = None,
    session: requests.Session | None = None,
    manifest: Path | None = None,
    page_size: int = 2000,
    force: bool = False,
) -> PullRecord | None:
    """Descarga una capa completa. Se salta si el GeoJSON ya existe con el sha256 del último registro."""
    s = session or requests.Session()
    layer = source["layer"]
    out_path = out_path or (config.DATA_RAW / "mgn" / f"{source['id'].replace('mgn-', '')}.geojson")
    prev = latest_record(source["id"], manifest)
    if prev and not force and out_path.exists() and sha256_of(out_path) == prev.sha256:
        return None
    features: list[dict] = []
    offset = 0
    while True:
        params = {
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": 4326,
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": page_size,
            "geometryPrecision": source.get("precision", 5),
        }
        if source.get("max_allowable_offset"):
            params["maxAllowableOffset"] = source["max_allowable_offset"]
        r = s.get(f"{SERVICE}/{layer}/query", params=params, timeout=TIMEOUT)
        r.raise_for_status()
        fc = r.json()
        if "error" in fc:
            raise RuntimeError(f"{source['id']}: el servicio devolvió error {fc['error']}")
        feats = fc.get("features", [])
        if feats and all(not f.get("geometry") for f in feats):
            raise RuntimeError(
                f"{source['id']}: el servicio devolvió rasgos sin geometría (¿MapServer en vez de FeatureServer?)"
            )
        features.extend(feats)
        # ArcGIS marca `exceededTransferLimit` (a veces bajo `properties`) cuando quedan páginas.
        more = fc.get("exceededTransferLimit", (fc.get("properties") or {}).get("exceededTransferLimit"))
        if not feats or len(feats) < page_size or more is False:
            break
        offset += page_size
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False), encoding="utf-8"
    )
    max_mb = float(source.get("max_file_mb", 45))
    if out_path.stat().st_size > max_mb * 1024 * 1024:
        raise RuntimeError(
            f"{source['id']}: {out_path.stat().st_size / 1e6:.1f} MB supera {max_mb} MB; sube max_allowable_offset"
        )
    when = now_iso()
    rec = PullRecord(
        pull_id=make_pull_id(source["id"], when),
        source_id=source["id"],
        dataset_id=f"MGN2024/{layer}",
        url=f"{SERVICE}/{layer}/query",
        params={
            "geometryPrecision": source.get("precision", 5),
            "maxAllowableOffset": source.get("max_allowable_offset"),
        },
        pulled_at=when,
        source_updated_at=None,
        row_count=len(features),
        bytes=out_path.stat().st_size,
        sha256=sha256_of(out_path),
        path=str(out_path.relative_to(config.REPO_ROOT))
        if out_path.is_relative_to(config.REPO_ROOT)
        else str(out_path),
        license=source.get("license", "DANE (sin licencia explícita; atribución)"),
    )
    append_record(rec, manifest)
    return rec


def geojson_attributes(path: Path):
    import pandas as pd

    fc = json.loads(Path(path).read_text(encoding="utf-8"))
    return pd.DataFrame([f["properties"] for f in fc["features"]])
