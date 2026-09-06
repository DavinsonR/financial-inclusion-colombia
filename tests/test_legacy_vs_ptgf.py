"""S13: reconstruir las nueve variables SFC del panel legado desde la tabla ptgf-ywrb descargada.

Hallazgo (B-031): el panel de la tesis es exactamente la suma de TODAS las filas de ptgf por
(departamento, trimestre, tipo), es decir, las filas municipales MÁS la fila de total departamental
(`renglon = 999`). Cada nivel SFC del panel vale el doble del valor real. La prueba fija ese hecho y
comprueba que los totales 999 coinciden con la suma municipal (la fuente es internamente consistente).
"""

from __future__ import annotations

import glob

import numpy as np
import pandas as pd
import pytest

from iif import config

RAW = config.DATA_RAW / "sfc_ptgf_ywrb"
pytestmark = [pytest.mark.data, pytest.mark.skipif(not RAW.exists(), reason="sin data/raw/sfc_ptgf_ywrb")]

# columna del panel legado -> (columna ptgf, bloque `tipo`)
LEGACY_TO_PTGF = {
    "NRO CORRESPONSALES ACTIVOS": ("corresactivos", "CORRESPONSALES"),
    "NRO DEPOSITOS": ("nrodepositos", "TRANS Y TRAMITES EN CORRESPONSALES"),
    "NRO PAGOS": ("nropagos", "TRANS Y TRAMITES EN CORRESPONSALES"),
    "NRO TRANSFERENCIAS": ("nrotrnsfer", "TRANS Y TRAMITES EN CORRESPONSALES"),
    "NRO TOTAL ": ("totalnrocorr", "TRANS Y TRAMITES EN CORRESPONSALES"),
    "NRO TOTAL CTA AHORROS": ("totalnroca", "CUENTAS DE AHORRO"),
    "MONTO TOTAL CREDITO CONSUMO": ("totalmontocdc", "CREDITO DE CONSUMO"),
    "MONTO TOTAL CREDITO VIVIENDA": ("totalmontocdv", "CREDITO DE VIVIENDA"),
    "MONTO TOTAL MICROCREDITO": ("totalmontomicro", "MICROCREDITO"),
}


@pytest.fixture(scope="module")
def frames():
    leg = pd.read_parquet(config.LEGACY_PARQUET)
    reg = pd.read_csv(config.SEEDS_DIR / "xw_departamento_region.csv", dtype=str)
    xw = pd.read_csv(config.SEEDS_DIR / "xw_sfc_departamento.csv", dtype=str)
    xw = xw[xw.fuente == "ptgf"]
    leg["dpto_ccdgo"] = leg["Depto Base"].map(dict(zip(reg.nombre_legacy, reg.dpto_ccdgo, strict=True)))
    assert leg.dpto_ccdgo.notna().all()
    leg["fechacorte"] = pd.to_datetime(leg["Fecha"]) + pd.offsets.MonthEnd(0)
    cols = sorted({c for c, _ in LEGACY_TO_PTGF.values()})
    raw = pd.concat(
        pd.read_parquet(f, columns=["fechacorte", "unicap", "renglon", "tipo", *cols])
        for f in sorted(glob.glob(str(RAW / "anio=*" / "part-0.parquet")))
    )
    raw = raw[raw.unicap.astype(int) <= 33].copy()
    raw["dpto_ccdgo"] = raw.unicap.astype(int).map(
        dict(zip(xw.unicap.astype(int), xw.dpto_ccdgo, strict=True))
    )
    raw["fechacorte"] = pd.to_datetime(raw.fechacorte)
    raw["es_total"] = raw.renglon.astype(int) == 999
    return leg.set_index(["dpto_ccdgo", "fechacorte"]), raw


def test_ptgf_covers_the_legacy_panel(frames):
    leg, raw = frames
    assert len(leg) == 462 and raw.fechacorte.nunique() == 14
    assert set(leg.index.get_level_values("fechacorte")) == set(raw.fechacorte)


def test_department_totals_equal_municipal_sums(frames):
    _, raw = frames
    cols = sorted({c for c, _ in LEGACY_TO_PTGF.values()})
    g = raw.groupby(["dpto_ccdgo", "fechacorte", "tipo", "es_total"])[cols].sum().unstack("es_total")
    for c in cols:
        tot, mun = g[(c, True)], g[(c, False)]
        rel = (tot - mun).abs() / mun.abs().replace(0, np.nan)
        assert (rel.dropna() < 1e-9).all(), c


@pytest.mark.parametrize("legacy_col", list(LEGACY_TO_PTGF))
def test_legacy_equals_twice_the_true_total(frames, legacy_col):
    """La tesis sumó municipios y total departamental: panel = 2 × total real, en las 462 filas."""
    leg, raw = frames
    pc, tipo = LEGACY_TO_PTGF[legacy_col]
    sub = raw[raw.tipo == tipo]
    todo = sub.groupby(["dpto_ccdgo", "fechacorte"])[pc].sum()
    real = sub[sub.es_total].groupby(["dpto_ccdgo", "fechacorte"])[pc].sum()
    m = leg[[legacy_col]].join(todo.rename("todo")).join(real.rename("real"))
    m[["todo", "real"]] = m[["todo", "real"]].fillna(
        0.0
    )  # sin filas en ptgf -> 0 en la tesis (ceros = faltantes)
    rel_todo = (m["todo"] - m[legacy_col]).abs() / m[legacy_col].abs().replace(0, np.nan)
    assert (rel_todo.dropna() <= 1e-6).all(), f"{legacy_col}: max {rel_todo.max():.2e}"
    nz = m[legacy_col] != 0
    ratio = (m.loc[nz, legacy_col] / m.loc[nz, "real"]).round(6)
    assert (ratio == 2.0).all(), (
        f"{legacy_col}: razón panel/real no es 2 en {int((ratio != 2.0).sum())} filas"
    )
