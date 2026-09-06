"""Descarga de archivos XLSX del DANE con captura de `Last-Modified` en el nombre (vintage)."""

from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests

from iif import config
from iif.acquire.manifest import PullRecord, append_record, latest_record, make_pull_id, now_iso, sha256_of

TIMEOUT = 300


def _last_modified(resp: requests.Response) -> str | None:
    lm = resp.headers.get("Last-Modified")
    if not lm:
        return None
    return parsedate_to_datetime(lm).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_file(
    source: dict,
    *,
    out_dir: Path | None = None,
    force: bool = False,
    session: requests.Session | None = None,
    manifest: Path | None = None,
) -> PullRecord | None:
    s = session or requests.Session()
    out_dir = out_dir or (config.DATA_RAW / source.get("folder", "dane"))
    url = source["url"]
    head = s.head(url, timeout=TIMEOUT, allow_redirects=True)
    lm = _last_modified(head) if head.ok else None
    prev = latest_record(source["id"], manifest)
    if prev and not force and lm and prev.source_updated_at == lm:
        return None
    r = s.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    lm = lm or _last_modified(r)
    stamp = (lm or now_iso())[:10].replace("-", "")
    name = Path(url.split("?")[0]).name
    stem, suffix = name.rsplit(".", 1) if "." in name else (name, "bin")
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{stem}__lm{stamp}.{suffix}"
    target.write_bytes(r.content)
    when = now_iso()
    rec = PullRecord(
        pull_id=make_pull_id(source["id"], when),
        source_id=source["id"],
        dataset_id=None,
        url=url,
        pulled_at=when,
        source_updated_at=lm,
        row_count=None,
        bytes=len(r.content),
        sha256=sha256_of(target),
        path=str(target.relative_to(config.REPO_ROOT))
        if target.is_relative_to(config.REPO_ROOT)
        else str(target),
        license=source.get("license", "DANE"),
        notes=source.get("notes", ""),
    )
    append_record(rec, manifest)
    return rec


def latest_file(source_id: str, manifest: Path | None = None) -> Path | None:
    rec = latest_record(source_id, manifest)
    return (config.REPO_ROOT / rec.path) if rec else None


def parse_datetime(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
