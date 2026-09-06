"""Parsers DANE y MGN: unidades sin datos, y pruebas `data` sobre las descargas reales si existen."""

from __future__ import annotations

import pandas as pd
import pytest

from iif import config
from iif.parse import dane
from iif.parse.dane import _code, _widen, _year_columns, normalize_name, parse_year


def test_parse_year_and_estado():
    assert parse_year("2024p") == (2024, "provisional")
    assert parse_year("2025pr") == (2025, "preliminar")
    assert parse_year(2019) == (2019, "definitivo")
    assert parse_year("2019.0") is None and parse_year("Total") is None and parse_year(None) is None


def test_year_columns_stop_at_first_gap():
    header = ("Código", "Depto", "2005", "2006", "2007pr", None, "Código", "Depto", "2005")
    assert _year_columns(header) == [
        (2, 2005, "definitivo"),
        (3, 2006, "definitivo"),
        (4, 2007, "preliminar"),
    ]


def test_code_and_name_normalization():
    assert _code(5, 2) == "05" and _code("05001", 5) == "05001" and _code("5001.0", 5) == "05001"
    assert _code("Fuente: DANE", 2) is None and _code(None, 2) is None
    assert normalize_name(" Bogotá, D.C. ") == "BOGOTA D C"
    assert normalize_name("Nariño") == normalize_name("NARINO")


def test_widen_uses_observed_combinations_only():
    long = pd.DataFrame(
        {
            "k": ["a", "a", "b"],
            "anio": [2020, 2020, 2021],
            "medida": ["x", "y", "x"],
            "valor": [1.0, 2.0, 3.0],
        }
    )
    wide = _widen(long, ["k", "anio"])
    assert len(wide) == 2 and wide.loc[wide.k == "b", "y"].isna().all()
    assert list(wide.columns) == ["k", "anio", "x", "y"]


_DANE = config.DATA_INTERIM / "dane"
_MGN = config.DATA_INTERIM / "mgn"
needs_data = pytest.mark.data


@needs_data
@pytest.mark.skipif(not (_DANE / "pib_departamento_anual.parquet").exists(), reason="sin data/interim/dane")
def test_dane_interim_tables_are_consistent():
    pib = pd.read_parquet(_DANE / "pib_departamento_anual.parquet")
    assert pib.dpto_ccdgo.nunique() == 34 and "00" in set(pib.dpto_ccdgo)  # 33 + Colombia
    assert pib.anio.min() == 2005 and pib.anio.max() >= 2024
    nacional = pib[pib.dpto_ccdgo == "00"].set_index("anio")["pib_corriente_mm"]
    suma = pib[pib.dpto_ccdgo != "00"].groupby("anio")["pib_corriente_mm"].sum()
    assert ((suma / nacional - 1).abs() < 1e-6).all(), "la suma de departamentos es el PIB nacional"

    va = pd.read_parquet(_DANE / "va_departamento_actividad_anual.parquet")
    assert va.dpto_ccdgo.nunique() == 33
    pib_dep = va[va.actividad.str.upper().str.startswith("PIB DEPARTAMENTAL")]
    chk = pib_dep.merge(pib, on=["dpto_ccdgo", "anio"], suffixes=("_va", "_pib"))
    assert ((chk.va_corriente_mm / chk.pib_corriente_mm - 1).abs() < 1e-6).all(), (
        "PIB por actividad = PIB total"
    )

    mun = pd.read_parquet(_DANE / "va_municipio_anual.parquet")
    assert mun.anio.min() == 2011 and mun.mpio_ccdgo.nunique() >= 1121
    assert (mun.mpio_ccdgo.str[:2] == mun.dpto_ccdgo).all()
    assert mun.peso_relativo_pct.notna().mean() > 0.99

    pob = pd.read_parquet(_DANE / "poblacion_municipio_anual.parquet")
    assert set(pob.fuente) == {"proyeccion_2018_2042", "retroproyeccion_2005_2017"}
    assert pob.anio.min() == 2005 and pob.anio.max() == 2042
    tot = pob[pob.area == "total"].groupby(["mpio_ccdgo", "anio"]).size()
    assert (tot == 1).all()

    itaed = pd.read_parquet(_DANE / "itaed_departamento_trimestre.parquet")
    assert {"00", "RESTO", "11", "05"} <= set(itaed.dpto_ccdgo) and itaed.dpto_ccdgo.nunique() == 15
    assert itaed.anio.min() == 2015


@needs_data
@pytest.mark.skipif(not (_MGN / "municipios.parquet").exists(), reason="sin data/interim/mgn")
def test_mgn_interim_matches_dane_codes():
    dep = pd.read_parquet(_MGN / "departamentos.parquet")
    mun = pd.read_parquet(_MGN / "municipios.parquet")
    assert len(dep) == 33 and len(mun) == 1121 and mun.mpio_ccdgo.str.len().eq(5).all()
    assert set(mun.dpto_ccdgo) == set(dep.dpto_ccdgo)
    va = pd.read_parquet(_DANE / "va_municipio_anual.parquet")
    extra = set(va.mpio_ccdgo) - set(mun.mpio_ccdgo)
    assert extra == {"27493", "94663"}, "Belén de Bajirá y Mapiripana existen en DANE pero no en MGN 2024"
    assert not (set(mun.mpio_ccdgo) - set(va.mpio_ccdgo))


def test_parse_all_fails_clearly_without_downloads(tmp_path):
    with pytest.raises(FileNotFoundError, match="iif acquire"):
        dane.parse_all(manifest=tmp_path / "vacio.jsonl", out_dir=tmp_path)
