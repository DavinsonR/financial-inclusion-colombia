import pytest

GOLDEN = {
    "A1": (20.8640, 5.9913, 429),
    "A2": (57.8769, 7.6273, 396),
    "A3": (0.3579, 6.2724, 396),
    "A4": (-8.4388, 6.9623, 429),
    "B1": (3.0349, 4.8141, 462),
    "B2": (35.5537, 5.9553, 429),
    "B3": (25.8399, 4.9779, 429),
    "B4": (-5.7504, 4.2043, 429),
}


@pytest.mark.parametrize("key", list(GOLDEN))
def test_tabla6_matches_notebook(legacy_results, key):
    beta, se, n = GOLDEN[key]
    r = legacy_results.tabla6[key]
    assert r is not None
    assert r.beta == pytest.approx(beta, rel=1e-3)
    assert r.se == pytest.approx(se, rel=1e-3)
    assert r.N == n


def test_sample_trace(legacy_results):
    t = legacy_results.trace
    assert t["crec_pib + IIF"] == 462
    assert t["crec_pib + IIF_lag1 + crec_pib_lag1"] == 429
    assert t["crec_pib_pc + IIF_lag1 + lag DV"] == 396


def test_two_way_kills_the_effect(legacy_results):
    a2, a3 = legacy_results.tabla6["A2"], legacy_results.tabla6["A3"]
    assert a2.p < 0.001 and a3.p > 0.9 and a2.N == a3.N


def test_regional_models_flag_few_clusters(legacy_results):
    reg = legacy_results.regional.set_index("Region")
    assert reg.loc["Pacífica", "N_dep"] == 4 and reg.loc["Orinoquía", "N_dep"] == 4
    assert reg.loc["Caribe", "beta"] == pytest.approx(72.2255, rel=1e-3)
