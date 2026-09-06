import pytest

from iif.legacy.constants import LABELS_PCA, VARS_PCA
from iif.legacy.index import build_pca_index


def test_index_matches_notebook(legacy_results):
    i = legacy_results.index
    assert i.kmo == pytest.approx(0.7189, rel=1e-3)
    assert i.bartlett == pytest.approx(2543.45, rel=1e-3)
    assert i.n_comp == 4
    assert i.var_ac[3] == pytest.approx(84.42, rel=1e-3)
    assert i.corr_orient == pytest.approx(0.8684, rel=1e-3)
    assert list(i.pesos.round(4)) == pytest.approx([0.5539, 0.2058, 0.1625, 0.0778], abs=1e-3)


def test_implied_weight_of_microcredit_is_negative(legacy_results):
    w = legacy_results.index.implied_weights
    assert w["Microcrédito/PIB"] < -0.2
    assert w["Cuentas ahorro"] > 0.25


def test_kaiser_retains_three(legacy_results):
    panel = legacy_results.index.scores.drop(columns=["IIF", "IIF_PC1", "log_IIF", "IIF_std"])
    res = build_pca_index(panel, VARS_PCA, ["departamento", "Fecha"], retention="kaiser", labels=LABELS_PCA)
    assert res.n_comp == 3


def test_standardize_scale_has_no_eps_outlier(legacy_results):
    panel = legacy_results.index.scores.drop(columns=["IIF", "IIF_PC1", "log_IIF", "IIF_std"])
    res = build_pca_index(panel, VARS_PCA, ["departamento", "Fecha"], scale="standardize", labels=LABELS_PCA)
    assert abs(res.scores["IIF"].mean()) < 1e-9
    assert res.scores["IIF"].min() > -5


def test_diagnostics_d2_d3(legacy_results):
    assert legacy_results.corr_iif_sin_net == pytest.approx(0.9933, rel=1e-3)
    assert legacy_results.corr_iif_oos == pytest.approx(0.9947, rel=1e-3)
