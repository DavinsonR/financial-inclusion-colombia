"""Atributos de las capas MGN (GeoJSON descargado por `iif acquire`) a Parquet tidy en data/interim/mgn/."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pandera.pandas as pa

from iif import config
from iif.acquire.manifest import latest_record
from iif.acquire.mgn import geojson_attributes

INTERIM = config.DATA_INTERIM / "mgn"

DEPARTAMENTO = pa.DataFrameSchema(
    {
        "dpto_ccdgo": pa.Column(str, pa.Check.str_matches(r"^\d{2}$"), unique=True),
        "dpto_cnmbr": pa.Column(str),
        "dpto_narea": pa.Column(float, pa.Check.gt(0), nullable=True),
    },
    coerce=True,
    strict=False,
)

MUNICIPIO = pa.DataFrameSchema(
    {
        "dpto_ccdgo": pa.Column(str, pa.Check.str_matches(r"^\d{2}$")),
        "mpio_ccdgo": pa.Column(str, pa.Check.str_matches(r"^\d{5}$"), unique=True),
        "mpio_cnmbr": pa.Column(str),
        "mpio_tipo": pa.Column(str, nullable=True),
        "mpio_narea": pa.Column(float, pa.Check.gt(0), nullable=True),
    },
    checks=[pa.Check(lambda df: (df["mpio_ccdgo"].str[:2] == df["dpto_ccdgo"]).all())],
    coerce=True,
    strict=False,
)


def _attrs(source_id: str, manifest: Path | None) -> pd.DataFrame:
    rec = latest_record(source_id, manifest)
    if rec is None:
        raise FileNotFoundError(
            f"{source_id}: no hay descarga en el manifiesto; corre `iif acquire {source_id}`"
        )
    df = geojson_attributes(config.REPO_ROOT / rec.path)
    df.columns = [c.lower() for c in df.columns]
    if "mpio_cdpmp" in df.columns:
        # En el MGN `mpio_ccdgo` son los 3 dígitos internos del departamento; el DIVIPOLA de 5 es `mpio_cdpmp`.
        df = df.drop(columns=["mpio_ccdgo"]).rename(columns={"mpio_cdpmp": "mpio_ccdgo"})
    return df.drop(columns=[c for c in ("objectid",) if c in df.columns])


def parse_all(manifest: Path | None = None, out_dir: Path | None = None) -> dict[str, Path]:
    out_dir = out_dir or INTERIM
    out_dir.mkdir(parents=True, exist_ok=True)
    dep = DEPARTAMENTO.validate(_attrs("mgn-departamentos", manifest))
    mun = MUNICIPIO.validate(_attrs("mgn-municipios", manifest))
    if len(dep) != 33:
        raise ValueError(f"MGN: se esperaban 33 departamentos, hay {len(dep)}")
    written = {
        "departamentos": out_dir / "departamentos.parquet",
        "municipios": out_dir / "municipios.parquet",
    }
    dep.sort_values("dpto_ccdgo").to_parquet(written["departamentos"], index=False)
    mun.sort_values("mpio_ccdgo").to_parquet(written["municipios"], index=False)
    return written
