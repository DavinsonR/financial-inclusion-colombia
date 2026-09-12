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


def _duckdb_path() -> Path:
    """La base analítica, con el mismo contrato que `dbt/profiles.yml`.

    dbt lee `IIF_DUCKDB_PATH` con `db/iif.duckdb` por defecto; el paquete tiene que leer exactamente la
    misma variable o construye la base en un sitio y la consulta en otro, que es lo que pasaba en CI, donde
    el flujo la pone en /tmp (R-15, B-055).
    """
    env = os.environ.get("IIF_DUCKDB_PATH")
    if env:
        ruta = Path(env)
        return ruta if ruta.is_absolute() else (REPO_ROOT / ruta)
    return REPO_ROOT / "db" / "iif.duckdb"


DUCKDB_PATH: Path = _duckdb_path()
SEEDS_DIR = DBT_DIR / "seeds"
DOCS_DIR = REPO_ROOT / "docs"
MANIFEST = DATA_RAW / "manifest.jsonl"
LEGACY_XLSX = DATA_LEGACY / "panel_fintech_colombia_trimestral.xlsx"
LEGACY_PARQUET = DATA_LEGACY / "panel_fintech_colombia_trimestral.parquet"


def load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}
