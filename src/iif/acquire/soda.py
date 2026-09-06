"""Descargas de datos.gov.co (Socrata / SODA 2.1) a Parquet particionado por año, con manifiesto.

Reglas: paginación estable con `$order=:id`; el conteo total se verifica con `count(*)`; una descarga
se salta si `rowsUpdatedAt` no cambió desde la última; todo valor llega como string y se tipa aquí;
ningún archivo supera `max_file_mb` (si lo hace se mueve a data/raw/_large/, que no va a git).
"""

from __future__ import annotations

import re
import shutil
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests

from iif import config
from iif.acquire.manifest import PullRecord, append_record, latest_record, make_pull_id, now_iso, sha256_of

BASE = "https://www.datos.gov.co"
DEFAULT_PAGE = 50_000
TIMEOUT = 180


class SizeGateError(RuntimeError):
    pass


def _session(session: requests.Session | None, app_token: str | None) -> requests.Session:
    s = session or requests.Session()
    if app_token:
        s.headers["X-App-Token"] = app_token
    s.headers.setdefault("User-Agent", "iif-colombia/0.1 (+https://github.com/DavinsonR)")
    return s


def soda_metadata(dataset_id: str, session: requests.Session | None = None) -> dict:
    s = _session(session, None)
    r = s.get(f"{BASE}/api/views/{dataset_id}.json", timeout=TIMEOUT)
    r.raise_for_status()
    meta = r.json()
    updated = meta.get("rowsUpdatedAt")
    return {
        "name": meta.get("name"),
        "rows_updated_at": datetime.fromtimestamp(updated, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        if updated
        else None,
        "license": (meta.get("license") or {}).get("name") or meta.get("licenseId"),
        "columns": [c.get("fieldName") for c in meta.get("columns", [])],
        "types": {c.get("fieldName"): c.get("dataTypeName") for c in meta.get("columns", [])},
    }


def soda_count(dataset_id: str, where: str | None = None, session: requests.Session | None = None) -> int:
    s = _session(session, None)
    params = {"$select": "count(*) as n"}
    if where:
        params["$where"] = where
    r = s.get(f"{BASE}/resource/{dataset_id}.json", params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return int(r.json()[0]["n"])


def iter_soda_pages(
    dataset_id: str,
    *,
    page_size: int = DEFAULT_PAGE,
    where: str | None = None,
    order: str = ":id",
    session: requests.Session | None = None,
    app_token: str | None = None,
) -> Iterator[list[dict]]:
    s = _session(session, app_token)
    offset = 0
    while True:
        params = {"$limit": page_size, "$offset": offset, "$order": order}
        if where:
            params["$where"] = where
        r = s.get(f"{BASE}/resource/{dataset_id}.json", params=params, timeout=TIMEOUT)
        r.raise_for_status()
        page = r.json()
        if not page:
            return
        yield page
        if len(page) < page_size:
            return
        offset += page_size


def type_frame(
    df: pd.DataFrame,
    *,
    numeric_regex: str | None,
    numeric_cols: list[str] | None,
    date_cols: list[str] | None,
    code_cols: list[str] | None = None,
) -> pd.DataFrame:
    df = df.copy()
    num = set(numeric_cols or [])
    if numeric_regex:
        num |= {c for c in df.columns if re.search(numeric_regex, c)}
    num -= set(code_cols or [])
    for c in num:
        if c in df.columns and not pd.api.types.is_numeric_dtype(df[c]):
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ".", regex=False), errors="coerce")
    for c in date_cols or []:
        if c in df.columns and not pd.api.types.is_datetime64_any_dtype(df[c]):
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def typing_from_metadata(source: dict, meta: dict) -> dict:
    """Tipado: columnas `number` y `calendar_date` según Socrata, más lo que diga config/sources.yaml.

    `code_cols` se mantienen como texto aunque Socrata las declare número (códigos DIVIPOLA, `unicap`,
    `renglon`, `codigo_entidad`): como número perderían los ceros a la izquierda y no son magnitudes.
    """
    types = meta.get("types") or {}
    code_cols = set(source.get("code_cols") or [])
    numeric = [c for c, t in types.items() if t == "number" and c not in code_cols]
    numeric += [c for c in (source.get("numeric_cols") or []) if c not in code_cols]
    dates = [c for c, t in types.items() if t == "calendar_date"] + list(source.get("date_cols") or [])
    return dict(
        numeric_regex=source.get("numeric_regex"),
        numeric_cols=sorted(set(numeric)),
        date_cols=sorted(set(dates)),
        code_cols=sorted(code_cols),
    )


def fetch_soda(
    source: dict,
    *,
    out_dir: Path | None = None,
    force: bool = False,
    session: requests.Session | None = None,
    manifest: Path | None = None,
) -> list[PullRecord]:
    """Descarga completa de una tabla SODA a `out_dir/<source>/anio=YYYY/part-0.parquet`."""
    out_dir = out_dir or config.DATA_RAW
    dataset_id = source["dataset"]
    source_id = source["id"]
    meta = soda_metadata(dataset_id, session)
    prev = latest_record(source_id, manifest)
    if prev and not force and meta["rows_updated_at"] and prev.source_updated_at == meta["rows_updated_at"]:
        return []
    where = source.get("where")
    expected = soda_count(dataset_id, where, session)
    typing = typing_from_metadata(source, meta)
    # Se tipa página a página: los números como float64 pesan 8 bytes; como texto, ~60 (kx2f trae 99 columnas).
    frames = [
        type_frame(pd.DataFrame(page), **typing)
        for page in iter_soda_pages(
            dataset_id, where=where, session=session, page_size=source.get("page_size", DEFAULT_PAGE)
        )
    ]
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if len(df) != expected:
        raise RuntimeError(f"{source_id}: descargadas {len(df)} filas, la fuente dice {expected}")
    df = type_frame(
        df, **typing
    )  # columnas ausentes en alguna página (Socrata omite nulos) quedan bien tipadas
    part_col = source.get("partition_col")
    if part_col and part_col not in df.columns:
        raise ValueError(
            f"{source_id}: la columna de partición {part_col!r} no existe; columnas: {sorted(df.columns)[:12]}..."
        )
    when = now_iso()
    pull_id = make_pull_id(source_id, when)
    df["pull_id"] = pull_id
    if part_col and part_col in df.columns:
        years = (
            pd.to_datetime(df[part_col], errors="coerce").dt.year
            if not pd.api.types.is_numeric_dtype(df[part_col])
            else df[part_col].astype(int)
        )
        groups = df.groupby(years.fillna(-1).astype(int))
    else:
        groups = [(None, df)]
    base = out_dir / source_id.replace("-", "_")
    if base.exists():
        shutil.rmtree(base)  # una descarga nueva reemplaza todas las particiones anteriores de la fuente
    records = []
    for year, part in groups:
        sub = base / (f"anio={int(year)}" if year is not None and year != -1 else "anio=sin_fecha")
        sub.mkdir(parents=True, exist_ok=True)
        target = sub / "part-0.parquet"
        part.to_parquet(target, index=False, compression="zstd")
        rec = _record_for(target, source, pull_id, when, meta, len(part), where)
        records.append(rec)
    max_mb = float(source.get("max_file_mb", 45))
    limit = max_mb * 1024 * 1024
    final: list[PullRecord] = []
    oversized = 0
    for r in records:
        target = _abs(r.path)
        if r.bytes > limit:
            oversized += 1
            big = out_dir / "_large" / target.relative_to(out_dir)
            big.parent.mkdir(parents=True, exist_ok=True)
            target.replace(big)
            r = replace(r, path=_rel(big), notes=f"supera {max_mb} MB: fuera de git (ADR-003)")
        append_record(r, manifest)
        final.append(r)
    if oversized:
        raise SizeGateError(
            f"{source_id}: {oversized} partición(es) superan {max_mb} MB y quedaron en {out_dir / '_large'}"
        )
    return final


def _rel(p: Path) -> str:
    return str(p.relative_to(config.REPO_ROOT)) if p.is_relative_to(config.REPO_ROOT) else str(p)


def _abs(p: str) -> Path:
    q = Path(p)
    return q if q.is_absolute() else config.REPO_ROOT / q


def _record_for(
    target: Path, source: dict, pull_id: str, when: str, meta: dict, n: int, where: str | None
) -> PullRecord:
    return PullRecord(
        pull_id=pull_id,
        source_id=source["id"],
        dataset_id=source["dataset"],
        url=f"{BASE}/resource/{source['dataset']}.json",
        params={"$order": ":id", "$where": where or ""},
        pulled_at=when,
        source_updated_at=meta["rows_updated_at"],
        row_count=n,
        bytes=target.stat().st_size,
        sha256=sha256_of(target),
        path=_rel(target),
        license=source.get("license", meta.get("license") or ""),
    )
