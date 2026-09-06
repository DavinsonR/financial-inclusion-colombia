import pytest

from iif import config
from iif.legacy.load import load_legacy_panel
from iif.legacy.variables import VariableOptions, build_variables


def test_d1_annual_repeated(legacy_results):
    d1 = legacy_results.d1
    assert d1["pib_pc_distintos_por_depto"] == {"min": 5, "max": 5, "media": 5.0}
    assert d1["frac_crec_identico_lag"] == pytest.approx(0.6429, rel=1e-3)
    assert legacy_results.frac_cero_crec_pc == pytest.approx(0.6434, rel=2e-3)


def test_urban_threshold_and_split(legacy_results):
    assert legacy_results.umbral_densidad == pytest.approx(102.97, rel=1e-3)


def test_corrected_mode_changes_the_deflator_and_internet():
    raw = load_legacy_panel(config.LEGACY_PARQUET)
    nb, _ = build_variables(raw, VariableOptions.for_mode("notebook"))
    co, _ = build_variables(raw, VariableOptions.for_mode("corrected"))
    # en modo notebook todos los departamentos comparten el mismo índice de precios por año
    assert nb.groupby("anio")["ipc_index"].nunique().max() == 1
    assert co.groupby("anio")["ipc_index"].nunique().max() > 1
    assert (nb["internet_pct"] == 0).sum() == 50
    assert co["internet_pct"].isna().sum() == 50
