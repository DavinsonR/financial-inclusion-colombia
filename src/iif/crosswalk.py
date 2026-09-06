"""Mapas derivados de las tablas de la SFC: bloque (`tipo`) a columnas, y claves geográficas.

- `derive_blocks`: para cada `tipo` (bloque de producto) de una fuente, las columnas numéricas con algún valor
  distinto de cero. Fuera de su bloque, una columna solo trae ceros estructurales (ADR-008): el mapa es lo que
  permite emitir un valor solo cuando la columna pertenece al bloque de la fila.
- `geo_report`: cobertura de `dpto_ccdgo || lpad(renglon, 3)` contra los códigos DIVIPOLA del MGN y del DANE, y
  lista de nombres que no coinciden tras normalizar (S-009, ADR-007).
"""

from __future__ import annotations

import glob
from pathlib import Path

import pandas as pd

from iif import config
from iif.parse.dane import normalize_name

FUENTES = {"ptgf": "sfc_ptgf_ywrb", "kx2f": "sfc_kx2f_xjdq"}
KEYS = {
    "ptgf": dict(fecha="fechacorte", unicap="unicap", renglon="renglon", municipio="municipio", tipo="tipo"),
    "kx2f": dict(
        fecha="fecha_corte", unicap="unicap", renglon="renglon", municipio="desc_renglon", tipo="tipo"
    ),
}


def _raw(fuente: str, columns: list[str] | None = None) -> pd.DataFrame:
    files = sorted(glob.glob(str(config.DATA_RAW / FUENTES[fuente] / "anio=*" / "part-0.parquet")))
    if not files:
        raise FileNotFoundError(
            f"{fuente}: no hay particiones en data/raw/{FUENTES[fuente]}; corre `iif acquire`"
        )
    return pd.concat((pd.read_parquet(f, columns=columns) for f in files), ignore_index=True)


def tipo_map(fuente: str) -> dict[str, str]:
    m = pd.read_csv(config.SEEDS_DIR / "map_sfc_tipo.csv", dtype=str, keep_default_na=False)
    m = m[m.fuente == fuente]
    return dict(zip(m.tipo_raw, m.tipo_id, strict=True))


def derive_blocks(fuente: str) -> pd.DataFrame:
    df = _raw(fuente)
    tipos = tipo_map(fuente)
    k = KEYS[fuente]
    num = [c for c in df.columns if df[c].dtype.kind in "fi" and c not in (k["unicap"], k["renglon"])]
    unknown = sorted(set(df[k["tipo"]].unique()) - set(tipos))
    if unknown:
        raise ValueError(f"{fuente}: valores de `tipo` sin fila en map_sfc_tipo.csv: {unknown}")
    out = []
    for tipo_raw, g in df.groupby(k["tipo"]):
        n = len(g)
        for c in num:
            nz = int((g[c].fillna(0) != 0).sum())
            if nz:
                out.append((fuente, tipos[tipo_raw], c, nz, round(nz / n, 4)))
    res = pd.DataFrame(out, columns=["fuente", "tipo_id", "columna", "n_no_cero", "frac_no_cero"])
    # Un mismo tipo_id puede venir de varias grafías de `tipo` (mojibake): se consolidan.
    res = res.groupby(["fuente", "tipo_id", "columna"], as_index=False).agg(
        n_no_cero=("n_no_cero", "sum"), frac_no_cero=("frac_no_cero", "max")
    )
    return res.sort_values(["fuente", "tipo_id", "columna"]).reset_index(drop=True)


def write_blocks(fuentes: list[str], path: Path | None = None) -> pd.DataFrame:
    """Escribe/actualiza dbt/seeds/map_sfc_columns.csv conservando las fuentes que no se recalculan."""
    path = path or config.SEEDS_DIR / "map_sfc_columns.csv"
    prev = (
        pd.read_csv(path, dtype={"fuente": str, "tipo_id": str, "columna": str})
        if path.exists()
        else pd.DataFrame()
    )
    parts = [prev[~prev.fuente.isin(fuentes)]] if len(prev) else []
    parts += [derive_blocks(f) for f in fuentes]
    res = pd.concat(parts, ignore_index=True).sort_values(["fuente", "tipo_id", "columna"])
    res.to_csv(path, index=False)
    return res


def geo_report(fuente: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(cobertura por trimestre, nombres que no coinciden) usando renglon como código municipal."""
    k = KEYS[fuente]
    df = _raw(fuente, columns=[k["fecha"], k["unicap"], k["renglon"], k["municipio"]])
    xw = pd.read_csv(config.SEEDS_DIR / "xw_sfc_departamento.csv", dtype=str)
    xw = xw[xw.fuente == fuente]
    u2d = dict(zip(xw.unicap.astype(int), xw.dpto_ccdgo, strict=True))
    geo = df[df[k["unicap"]].astype(int) <= 33].copy()
    geo["dpto_ccdgo"] = geo[k["unicap"]].astype(int).map(u2d)
    geo["renglon_i"] = geo[k["renglon"]].astype(int)
    mun = geo[geo.renglon_i != 999].copy()
    mun["mpio_ccdgo"] = mun.dpto_ccdgo + mun.renglon_i.map(lambda x: f"{x:03d}")
    dane = pd.read_parquet(
        config.DATA_INTERIM / "dane" / "poblacion_municipio_anual.parquet",
        columns=["mpio_ccdgo", "municipio"],
    ).drop_duplicates("mpio_ccdgo")
    mgn = pd.read_parquet(config.DATA_INTERIM / "mgn" / "municipios.parquet", columns=["mpio_ccdgo"])
    known = set(dane.mpio_ccdgo) | set(mgn.mpio_ccdgo)
    mun["mapeado"] = mun.mpio_ccdgo.isin(known)
    cov = mun.groupby(k["fecha"]).agg(filas=("mapeado", "size"), mapeadas=("mapeado", "sum"))
    cov["cobertura"] = (cov.mapeadas / cov.filas).round(6)
    names = (
        mun[["mpio_ccdgo", k["municipio"]]]
        .drop_duplicates()
        .merge(dane, on="mpio_ccdgo", how="left", suffixes=("_sfc", "_dane"))
    )
    names.columns = ["mpio_ccdgo", "nombre_sfc", "nombre_dane"]
    names["coincide"] = names.nombre_sfc.map(normalize_name) == names.nombre_dane.fillna("").map(
        normalize_name
    )
    names["en_dane_o_mgn"] = names.mpio_ccdgo.isin(known)
    return cov.reset_index(), names[~names.coincide].sort_values("mpio_ccdgo").reset_index(drop=True)
