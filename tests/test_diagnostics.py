import numpy as np
import pandas as pd
import pytest

from iif.legacy import diagnostics as dg


def test_pesaran_cd_matches(legacy_results):
    assert legacy_results.pesaran["CD"] == pytest.approx(69.1165, rel=1e-3)
    assert legacy_results.pesaran["N"] == 33


def test_hausman_is_flagged_invalid(legacy_results):
    h = legacy_results.hausman
    assert h is not None and h.valid is False
    assert h.chi2 == pytest.approx(292.7736, rel=1e-3)


def test_hausman_warns():
    idx = pd.MultiIndex.from_product(
        [[f"d{i}" for i in range(6)], pd.period_range("2018Q1", periods=8, freq="Q").to_timestamp()]
    )
    rng = np.random.default_rng(0)
    df = pd.DataFrame(
        {"crec_pib": rng.normal(size=48), "x": rng.normal(size=48), "crec_pib_lag1": rng.normal(size=48)},
        index=idx,
    )
    with pytest.warns(UserWarning, match="Hausman"):
        dg.hausman_clustered(df, "crec_pib_lag1 + x")


def test_mundlak_and_correlations(legacy_results):
    assert legacy_results.mundlak["beta_mean"] == pytest.approx(6.7960, rel=1e-3)
    assert legacy_results.corr_between == pytest.approx(0.1201, rel=1e-3)
    assert legacy_results.corr_within == pytest.approx(-0.1532, rel=1e-3)


def test_nickell_formula():
    r = dg.nickell_bias(0.4279, 14)
    assert r["sesgo"] == pytest.approx(-0.1098, rel=1e-3)


def test_driscoll_kraay_blows_up_the_se(legacy_results):
    dk = legacy_results.dk_vs_cluster
    assert dk["clustered"] == pytest.approx(5.9553, rel=1e-3)
    assert dk["driscoll_kraay"] == pytest.approx(37.0221, rel=1e-2)
