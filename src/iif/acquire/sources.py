from __future__ import annotations

from pathlib import Path

from iif import config


def load_sources(path: Path | None = None) -> dict[str, dict]:
    cfg = config.load_yaml(path or config.CONFIG_DIR / "sources.yaml")
    return cfg["sources"]


def get_source(source_id: str, path: Path | None = None) -> dict:
    sources = load_sources(path)
    if source_id not in sources:
        raise KeyError(f"fuente desconocida: {source_id}. Conocidas: {sorted(sources)}")
    return {"id": source_id, **sources[source_id]}
