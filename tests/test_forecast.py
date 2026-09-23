"""Pruebas de la capa de proyección.

Se prueban propiedades que se pueden verificar sin correr el modelo completo —la
reconciliación suma exacto, la combinación no estrecha el intervalo, la puerta de calidad
levanta— y una sola prueba lenta de extremo a extremo marcada para poder saltarla.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from iif.forecast import backtest, frame, models, reconcile


@pytest.fixture(scope="module")
def marco():
    if not frame.PIB_DEPARTAMENTO.exists():
        pytest.skip("falta data/interim/dane/pib_departamento_anual.parquet")
    return frame.load_frame()


# ------------------------------------------------------------------ marco y vintage

def test_marco_es_panel_completo(marco):
    assert marco.log_pib.notna().all().all()
    assert marco.pib_nivel.shape == marco.log_pib.shape
    assert len(marco.departamentos) == 33


def test_vintage_registra_el_estado_del_dato(marco):
    """ADR-019 decisión 3: sin vintage, la revisión de 2024 y 2025 invalida el histórico."""
    v = marco.vintage.as_dict()
    assert len(v["sha256"]) == 64
    assert v["n_departamentos"] == 33
    assert set(v["estado_por_anio"].values()) <= {"definitivo", "provisional", "preliminar"}
    # los dos años que el DANE aún revisa tienen que estar marcados como tales
    assert v["estado_por_anio"].get("2024") != "definitivo"


def test_dummies_marcan_solo_los_anios_declarados():
    d = frame.dummies_atipicos([2018, 2019, 2020, 2021, 2022])
    assert d.shape == (5, 2)
    assert d[:, 0].tolist() == [0, 0, 1, 0, 0]   # 2020
    assert d[:, 1].tolist() == [0, 0, 0, 1, 0]   # 2021


def test_dummies_valen_cero_en_el_horizonte():
    """Al proyectar 2026-2028 las dummies no aportan por sí mismas (ADR-020, consecuencias)."""
    assert frame.dummies_atipicos([2026, 2027, 2028]).sum() == 0


# ------------------------------------------------------------------ reconciliación

def test_reparto_proporcional_suma_exacto():
    base = np.array([100.0, 50.0, 25.0, 5.0])
    ajustado = reconcile.reparto_proporcional(base, 200.0)
    assert ajustado.sum() == pytest.approx(200.0, rel=1e-12)


def test_reparto_proporcional_no_altera_el_patron():
    """Propiedad central: el ancla desplaza el nivel común y no reordena el mapa."""
    base = np.array([100.0, 50.0, 25.0, 5.0])
    ajustado = reconcile.reparto_proporcional(base, 200.0)
    assert np.allclose(ajustado / ajustado.sum(), base / base.sum())
    factores = ajustado / base
    assert np.allclose(factores, factores[0])


def test_mint_tambien_suma_exacto_pero_reparte_distinto():
    base = np.array([100.0, 50.0, 25.0, 5.0])
    var = np.array([0.001, 0.004, 0.01, 0.05])
    prop = reconcile.reparto_proporcional(base, 200.0)
    mint = reconcile.reparto_mint_diagonal(base, var, 200.0)
    assert mint.sum() == pytest.approx(200.0, rel=1e-12)
    assert not np.allclose(prop, mint)


def test_ancla_encadena_el_crecimiento():
    ancla = reconcile.Ancla("prueba", "2026-01-01", {2026: 10.0, 2027: 10.0})
    niveles = ancla.niveles(100.0, 2025, [2026, 2027])
    assert niveles[2026] == pytest.approx(110.0)
    assert niveles[2027] == pytest.approx(121.0)


def test_ancla_se_queja_si_no_cubre_el_horizonte():
    ancla = reconcile.Ancla("prueba", "2026-01-01", {2026: 2.0})
    with pytest.raises(KeyError):
        ancla.niveles(100.0, 2025, [2026, 2027])


def test_coherencia_es_exacta_en_la_ventana_de_reconciliacion(marco):
    """ADR-021: ≤0,072 % desde 2018; en los años retropolados llega a 1,28 % y se sabe."""
    brecha = reconcile.coherencia(marco.pib_nivel, marco.nacional).abs()
    assert brecha.loc[2018:].max() < 0.1
    assert brecha.loc[2005:2012].max() > 0.2


# ------------------------------------------------------------------ modelos

def test_referencias_devuelven_el_horizonte_pedido():
    serie = pd.Series(np.log(np.linspace(100, 150, 20)), index=range(2005, 2025))
    for fn in (models.naive, models.drift):
        p = fn(serie, 3)
        assert p.media.shape == (3,) and p.varianza.shape == (3,)
        assert np.all(np.isfinite(p.media))


def test_la_varianza_crece_con_el_horizonte():
    serie = pd.Series(np.log(np.linspace(100, 150, 20)), index=range(2005, 2025))
    p = models.drift(serie, 3)
    assert p.varianza[0] < p.varianza[1] < p.varianza[2]


def test_combinar_no_estrecha_el_intervalo():
    """La varianza de la mezcla incluye el desacuerdo entre modelos (ADR-022)."""
    a = models.Pronostico(np.array([1.0]), np.array([0.04]))
    b = models.Pronostico(np.array([1.4]), np.array([0.04]))
    c = models.combinar({"a": a, "b": b})
    assert c.media[0] == pytest.approx(1.2)
    assert c.varianza[0] > 0.04           # media de varianzas más el desacuerdo
    assert c.varianza[0] == pytest.approx(0.04 + 0.04)


def test_combinar_sobrevive_a_una_especificacion_caida():
    viva = models.Pronostico(np.array([1.0]), np.array([0.01]))
    caida = models.Pronostico(np.array([np.nan]), np.array([np.nan]))
    c = models.combinar({"viva": viva, "caida": caida})
    assert c.media[0] == pytest.approx(1.0)


def test_predecir_no_lanza_con_una_serie_imposible():
    serie = pd.Series([1.0, 1.0, 1.0], index=[2023, 2024, 2025])
    p = models.predecir("arima_210_atipicos", serie, 3)
    assert p.media.shape == (3,)


def test_intervalo_al_95_es_mas_ancho_que_al_80():
    p = models.Pronostico(np.array([2.0]), np.array([0.25]))
    bajo80, alto80 = p.intervalo(0.80)
    bajo95, alto95 = p.intervalo(0.95)
    assert bajo80[0] < 2.0 < alto80[0]
    assert (alto95[0] - bajo95[0]) > (alto80[0] - bajo80[0])


# ------------------------------------------------------------------ puerta de calidad

def _detalle(ganancia: bool, cobertura: float = 1.0) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    filas = []
    for cod in [f"{i:02d}" for i in range(1, 21)]:
        for origen in range(2018, 2026):
            ref = float(rng.normal(0, 4))
            mio = ref * (0.5 if ganancia else 1.8)
            if rng.random() > cobertura:
                mio = np.nan
            filas.append(dict(dpto_ccdgo=cod, origen=origen, modelo="ingenuo",
                              real=0.0, pronostico=ref, error=ref))
            filas.append(dict(dpto_ccdgo=cod, origen=origen, modelo="combinacion",
                              real=0.0, pronostico=mio, error=mio))
    return pd.DataFrame(filas)


def test_la_puerta_deja_pasar_un_modelo_que_gana():
    v = backtest.evaluar(_detalle(ganancia=True))
    aprobado = backtest.exigir_aprobacion(v, "combinacion")
    assert aprobado.ganancia_pct > 0
    assert aprobado.dm_p < 0.05


def test_la_puerta_frena_un_modelo_que_pierde():
    v = backtest.evaluar(_detalle(ganancia=False))
    with pytest.raises(backtest.PuertaDeCalidad):
        backtest.exigir_aprobacion(v, "combinacion")


def test_la_puerta_frena_por_cobertura_aunque_el_mae_sea_bajo():
    """Un modelo que solo responde en los orígenes fáciles no compitió (B-001 del laboratorio)."""
    v = backtest.evaluar(_detalle(ganancia=True, cobertura=0.5))
    combinacion = next(x for x in v if x.modelo == "combinacion")
    assert combinacion.cobertura < backtest.MIN_COBERTURA
    assert not combinacion.aprobado
    with pytest.raises(backtest.PuertaDeCalidad):
        backtest.exigir_aprobacion(v, "combinacion")


def test_diebold_mariano_calla_sin_pares_suficientes():
    idx = pd.MultiIndex.from_product([["01"], range(2020, 2023)], names=["dpto_ccdgo", "origen"])
    a = pd.Series([1.0, 2.0, 3.0], index=idx)
    ganancia, p = backtest.diebold_mariano(a, a)
    assert ganancia is None and p is None


# ------------------------------------------------------------------ extremo a extremo

@pytest.mark.slow
def test_la_combinacion_supera_al_ingenuo_en_el_panel_real(marco):
    """La afirmación de ADR-020 que el módulo publica, comprobada sobre los datos."""
    detalle = backtest.rolling_origin(marco)
    veredictos = backtest.evaluar(detalle)
    aprobado = backtest.exigir_aprobacion(veredictos, "combinacion")
    assert aprobado.cobertura == 1.0
    assert aprobado.ganancia_pct > 20
    assert aprobado.dm_p < 0.01
