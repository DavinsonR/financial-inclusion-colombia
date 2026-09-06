"""Rutas y configuración del proyecto. Nunca rutas absolutas en el código: todo cuelga de REPO_ROOT."""

from __future__ import annotations

import os
from pathlib import Path

import yaml


def _find_root() -> Path:
    env = os.environ.get("IIF_ROOT")
    if env:
        return Path(env).resolve()
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


REPO_ROOT: Path = _find_root()
CONFIG_DIR = REPO_ROOT / "config"
DATA_DIR = REPO_ROOT / "data"
DATA_LEGACY = DATA_DIR / "legacy"
DATA_RAW = DATA_DIR / "raw"
DATA_INTERIM = DATA_DIR / "interim"
DATA_PROCESSED = DATA_DIR / "processed"
DBT_DIR = REPO_ROOT / "dbt"
SEEDS_DIR = DBT_DIR / "seeds"
DOCS_DIR = REPO_ROOT / "docs"
MANIFEST = DATA_RAW / "manifest.jsonl"
LEGACY_XLSX = DATA_LEGACY / "panel_fintech_colombia_trimestral.xlsx"
LEGACY_PARQUET = DATA_LEGACY / "panel_fintech_colombia_trimestral.parquet"


def load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}
