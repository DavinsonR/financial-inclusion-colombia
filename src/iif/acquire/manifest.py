from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from iif import config


@dataclass(frozen=True)
class PullRecord:
    pull_id: str
    source_id: str
    dataset_id: str | None
    url: str
    params: dict = field(default_factory=dict)
    pulled_at: str = ""
    source_updated_at: str | None = None
    row_count: int | None = None
    bytes: int = 0
    sha256: str = ""
    path: str = ""
    license: str = ""
    tool: str = "iif 0.1.0"
    notes: str = ""


def now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_pull_id(source_id: str, when: str | None = None) -> str:
    """`<fuente>__<UTC al segundo>_<4 hex>`: el sufijo evita colisiones entre descargas del mismo segundo."""
    stamp = (when or now_iso()).replace("-", "").replace(":", "")
    return f"{source_id}__{stamp}_{secrets.token_hex(2)}"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def append_record(rec: PullRecord, manifest: Path | None = None) -> None:
    manifest = manifest or config.MANIFEST
    manifest.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")


def read_records(manifest: Path | None = None) -> list[PullRecord]:
    manifest = manifest or config.MANIFEST
    if not manifest.exists():
        return []
    out = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(PullRecord(**json.loads(line)))
    return out


def latest_record(source_id: str, manifest: Path | None = None) -> PullRecord | None:
    recs = [r for r in read_records(manifest) if r.source_id == source_id]
    return recs[-1] if recs else None


def latest_records(manifest: Path | None = None) -> list[PullRecord]:
    """Los registros de la última descarga (mismo `pull_id`) de cada fuente; las anteriores quedan superadas."""
    records = read_records(manifest)
    newest: dict[str, str] = {}
    for r in records:  # el manifiesto solo crece: el último registro de cada fuente es su descarga vigente
        newest[r.source_id] = r.pull_id
    return [r for r in records if r.pull_id == newest[r.source_id]]


def verify_manifest(manifest: Path | None = None, root: Path | None = None) -> list[str]:
    """Problemas en la última descarga de cada fuente: archivo ausente o sha256 distinto al registrado."""
    root = root or config.REPO_ROOT
    problems = []
    for r in latest_records(manifest):
        p = root / r.path
        if not p.exists():
            problems.append(f"falta {r.path} ({r.pull_id})")
        elif r.sha256 and sha256_of(p) != r.sha256:
            problems.append(f"sha256 distinto en {r.path} ({r.pull_id})")
    return problems
