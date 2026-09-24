"""Pruebas de la capa de proyección.

Se prueban propiedades que se pueden verificar sin correr el modelo completo —la
reconciliación suma exacto, la combinación no estrecha el intervalo, la puerta de calidad
levanta— y una sola prueba lenta de extremo a extremo marcada para poder saltarla.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from iif import config
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


def _detalle_con_choque_comun(diferencia_por_origen: dict[int, float], n_dptos: int = 33,
                              seed: int = 11) -> pd.DataFrame:
    """Diferencias de error absoluto = choque del año + ruido propio: la estructura de B-065.

    El modelo no tiene ninguna ventaja propia; todo lo que lo separa del ingenuo es el choque
    que comparten los departamentos de un mismo origen.
    """
    rng = np.random.default_rng(seed)
    filas = []
    for origen, choque in diferencia_por_origen.items():
        for i in range(n_dptos):
            ref = 20.0 + float(rng.normal(0, 1))
            mio = ref + choque + float(rng.normal(0, 1))
            cod = f"{i:02d}"
            filas.append(dict(dpto_ccdgo=cod, origen=origen, modelo="ingenuo",
                              real=0.0, pronostico=ref, error=ref))
            filas.append(dict(dpto_ccdgo=cod, origen=origen, modelo="combinacion",
                              real=0.0, pronostico=mio, error=mio))
    return pd.DataFrame(filas)


# El patrón del panel real (ADR-023): casi toda la ventaja está en el año de recuperación.
PATRON_REAL = {2018: 0.33, 2019: 0.03, 2020: 0.59, 2021: -14.94,
               2022: -1.15, 2023: -2.22, 2024: 0.13, 2025: 0.11}


def test_diebold_mariano_agrupa_por_origen_y_no_confunde_un_choque_comun_con_ventaja():
    """Con un choque común por año, la t sobre pares independientes rechaza y la por origen no."""
    detalle = _detalle_con_choque_comun(PATRON_REAL)
    w = detalle.pivot_table(index=["dpto_ccdgo", "origen"], columns="modelo", values="error")
    p_pares = stats.ttest_1samp(w.combinacion.abs() - w.ingenuo.abs(), 0.0).pvalue
    assert p_pares < 1e-6  # la premisa: la prueba vieja lo da por significativo

    idx = ["dpto_ccdgo", "origen"]
    ganancia, p = backtest.diebold_mariano(
        detalle[detalle.modelo == "combinacion"].set_index(idx).error,
        detalle[detalle.modelo == "ingenuo"].set_index(idx).error)
    assert ganancia > 0
    assert p > 0.2


def test_la_puerta_informa_los_origenes_y_el_mejor_anio():
    v = backtest.evaluar(_detalle_con_choque_comun(PATRON_REAL))
    combinacion = next(x for x in v if x.modelo == "combinacion")
    assert (combinacion.origenes_ganados, combinacion.n_origenes) == (3, 8)
    assert combinacion.mejor_origen == 2021
    assert combinacion.ganancia_sin_mejor_origen_pct > 0
    assert combinacion.aprobado  # la puerta de ADR-023 no exige significancia


def test_la_puerta_frena_una_ganancia_que_es_un_solo_anio():
    """Pierde un poco todos los años y gana mucho en uno: sin ese año, no hay ventaja."""
    patron = {a: 0.5 for a in range(2018, 2025)} | {2025: -15.0}
    v = backtest.evaluar(_detalle_con_choque_comun(patron))
    combinacion = next(x for x in v if x.modelo == "combinacion")
    assert combinacion.ganancia_pct > 0
    assert combinacion.ganancia_sin_mejor_origen_pct < 0
    assert not combinacion.aprobado
    with pytest.raises(backtest.PuertaDeCalidad):
        backtest.exigir_aprobacion(v, "combinacion")


def test_diebold_mariano_calla_con_menos_de_tres_origenes():
    detalle = _detalle_con_choque_comun({2020: -1.0, 2021: -2.0})
    idx = ["dpto_ccdgo", "origen"]
    ganancia, p = backtest.diebold_mariano(
        detalle[detalle.modelo == "combinacion"].set_index(idx).error,
        detalle[detalle.modelo == "ingenuo"].set_index(idx).error)
    assert ganancia > 0 and p is None


def test_la_lectura_publicada_no_deja_sola_la_ganancia():
    from iif.forecast.run import lectura_de_la_puerta

    v = backtest.Veredicto("combinacion", 3.4, 1.0, 38.5539, 0.287, 264, True,
                           origenes_ganados=3, n_origenes=8, mejor_origen=2021,
                           ganancia_sin_mejor_origen_pct=8.29)
    texto = lectura_de_la_puerta(v)
    assert "38,6 %" in texto and "3 de 8" in texto and "sin 2021" in texto and "+8,3 %" in texto
    assert "no es estadísticamente distinguible" in texto and "p = 0,29" in texto


# ------------------------------------------------------------------ auditoría: fallos que no avisaban

def _marco_sintetico(anios=range(2005, 2026), nacional_hasta: int | None = None) -> frame.Marco:
    """Un departamento con crecimiento de 3 % hasta 2019 y de 10 % desde 2020: verdad conocida."""
    anios = list(anios)
    g = np.array([0.03 if a < 2020 else 0.10 for a in anios])
    log_pib = pd.DataFrame({"01": np.log(100.0) + np.cumsum(g)}, index=pd.Index(anios, name="anio"))
    nivel = np.exp(log_pib)
    fin = nacional_hasta if nacional_hasta is not None else anios[-1]
    nacional = nivel["01"].loc[:fin]
    vintage = frame.Vintage("sintetico", "0" * 64, anios[0], anios[-1], 1)
    return frame.Marco(log_pib, nivel, nacional, {"01": "Uno"}, vintage)


def test_rolling_origin_a_h_pasos_mide_el_anio_objetivo():
    """Con h=2 el error es el del segundo año, no el del primero con la etiqueta cambiada."""
    marco = _marco_sintetico()
    d1 = backtest.rolling_origin(marco, primer_origen=2022, h=1, modelos=["ingenuo"])
    d2 = backtest.rolling_origin(marco, primer_origen=2022, h=2, modelos=["ingenuo"])
    serie = marco.log_pib["01"]
    fila = d2[d2.origen == 2022].iloc[0]
    assert fila.real == pytest.approx(serie.loc[2023])
    # el ingenuo repite el último crecimiento (10 %) dos veces desde 2021
    assert fila.pronostico == pytest.approx(serie.loc[2021] + 2 * 0.10)
    assert fila.error == pytest.approx(0.0, abs=1e-9)
    # el último origen a dos pasos no existe: su objetivo cae fuera de la muestra
    assert d2.origen.max() == 2024 and d1.origen.max() == 2025
    assert {"varianza", "pronostico", "real"} <= set(d2.columns)
    with pytest.raises(ValueError):
        backtest.rolling_origin(marco, h=0)


def test_cobertura_del_intervalo_se_mide_contra_la_verdad():
    """Errores normales con la varianza correcta cubren el 80 %; con la cuarta parte, mucho menos."""
    rng = np.random.default_rng(11)
    n = 4000
    real = rng.normal(0, 0.03, n)
    base = pd.DataFrame(dict(dpto_ccdgo="01", origen=np.arange(n), real=real, pronostico=0.0))
    bien = base.assign(modelo="bien", varianza=0.03 ** 2)
    corto = base.assign(modelo="corto", varianza=(0.03 / 2) ** 2)
    caido = base.iloc[:10].assign(modelo="caido", pronostico=np.nan, varianza=np.nan)
    cob = backtest.cobertura_intervalo(pd.concat([bien, corto, caido]), 0.80).set_index("modelo")
    assert cob.loc["bien", "cobertura_empirica"] == pytest.approx(0.80, abs=0.02)
    assert cob.loc["corto", "cobertura_empirica"] < 0.55
    assert "caido" not in cob.index, "sin pronóstico no hay intervalo que evaluar"


def test_predecir_rechaza_un_nombre_desconocido():
    """Un nombre mal escrito no es un fallo de convergencia y no se disfraza de NaN."""
    serie = pd.Series(np.log(np.linspace(100, 150, 20)), index=range(2005, 2025))
    with pytest.raises(KeyError):
        models.predecir("arima_110_atipcos", serie, 1)


def test_reparto_proporcional_no_deja_pasar_la_base_sin_anclar():
    """Antes devolvía la base intacta con un objetivo NaN: el mapa 'reconciliado' no lo estaba."""
    base = np.array([100.0, 50.0])
    with pytest.raises(ValueError):
        reconcile.reparto_proporcional(base, float("nan"))
    with pytest.raises(ValueError):
        reconcile.reparto_proporcional(np.array([100.0, np.nan]), 200.0)
    with pytest.raises(ValueError):
        reconcile.reparto_proporcional(np.array([0.0, 0.0]), 200.0)
    with pytest.raises(ValueError):
        reconcile.reparto_mint_diagonal(base, np.array([0.01, np.nan]), 200.0)


def test_el_horizonte_tiene_que_seguir_al_ultimo_dato():
    """Un panel que llega a 2024 no puede publicar su primer paso como 2026."""
    from iif.forecast import run

    run._exigir_horizonte_contiguo(_marco_sintetico(), [2026, 2027, 2028])
    corto = _marco_sintetico(anios=range(2005, 2025))
    with pytest.raises(ValueError, match="no sigue"):
        run._exigir_horizonte_contiguo(corto, [2026, 2027, 2028])
    with pytest.raises(ValueError, match="no sigue"):
        run.pronosticar(corto, [2026, 2027, 2028])
    with pytest.raises(ValueError, match="no sigue"):
        run._exigir_horizonte_contiguo(_marco_sintetico(), [2026, 2028])


def test_el_total_nacional_tiene_que_llegar_al_ultimo_anio():
    """Si el nacional termina un año antes, el ancla se saltaría un año de crecimiento."""
    from iif.forecast import run

    run._exigir_nacional_al_dia(_marco_sintetico())
    with pytest.raises(ValueError, match="total nacional"):
        run._exigir_nacional_al_dia(_marco_sintetico(nacional_hasta=2024))


def test_el_marco_no_promedia_filas_repetidas(tmp_path):
    """`pivot_table` promediaba en silencio dos versiones del mismo año."""
    filas = [dict(dpto_ccdgo=c, anio=a, pib_constante_2015_mm=100.0 + a - 2005,
                  estado_dato="definitivo", departamento=c)
             for c in ("00", "05") for a in range(2005, 2010)]
    filas.append(dict(filas[-1], pib_constante_2015_mm=999.0))
    ruta = tmp_path / "pib.parquet"
    pd.DataFrame(filas).to_parquet(ruta)
    with pytest.raises(ValueError, match="repite"):
        frame._sin_duplicados(pd.read_parquet(ruta), ruta)


# ------------------------------------------------------------------ extremo a extremo

@pytest.mark.slow
def test_la_combinacion_supera_al_ingenuo_en_el_panel_real(marco):
    """Las afirmaciones de ADR-020 y ADR-023 que el módulo publica, comprobadas sobre los datos."""
    detalle = backtest.rolling_origin(marco)
    veredictos = backtest.evaluar(detalle)
    aprobado = backtest.exigir_aprobacion(veredictos, "combinacion")
    assert aprobado.cobertura == 1.0
    assert aprobado.ganancia_pct > 20
    # Las cifras de ADR-023 (R-09): la ventaja se concentra en 2021 y, agrupada por
    # origen, no es significativa con ocho años.
    assert (aprobado.origenes_ganados, aprobado.n_origenes) == (3, 8)
    assert aprobado.mejor_origen == 2021
    assert 5 < aprobado.ganancia_sin_mejor_origen_pct < 12
    assert 0.2 < aprobado.dm_p < 0.4


# ------------------------------------------------------------------ ancho del crecimiento anual (A4)

def test_en_un_paseo_aleatorio_el_crecimiento_no_acumula_varianza():
    """La del nivel suma los choques; la del crecimiento de cada año es la de un choque."""
    serie = pd.Series(np.log(np.linspace(100, 150, 20)) + np.random.default_rng(3).normal(0, 0.02, 20),
                      index=range(2005, 2025))
    for fn in (models.naive, models.drift):
        p = fn(serie, 3)
        assert np.allclose(p.varianza_crecimiento, p.varianza[0])
        assert np.allclose(p.varianza, np.cumsum(p.varianza_crecimiento))


def test_la_varianza_del_crecimiento_arima_cuadra_con_la_del_nivel_de_statsmodels():
    """Los pesos ψ reconstruyen la varianza del nivel que da statsmodels, y la del crecimiento es menor.

    Es la comprobación de que las dos varianzas salen del mismo ajuste: σ² Σ (ψ_0 + … + ψ_j)² es la del
    nivel; σ² Σ ψ_j², la del crecimiento de cada año.
    """
    rng = np.random.default_rng(5)
    e = rng.normal(0, 0.02, 40)
    d = np.empty(40)
    d[0] = 0.03
    for t in range(1, 40):
        d[t] = 0.03 + 0.5 * (d[t - 1] - 0.03) + e[t]
    serie = pd.Series(np.log(100.0) + np.cumsum(d), index=range(1986, 2026))
    p = models.predecir("arima_110_atipicos", serie, 3)
    assert np.all(np.isfinite(p.varianza_crecimiento))
    assert p.varianza_crecimiento[0] == pytest.approx(p.varianza[0])
    from statsmodels.tsa.arima.model import ARIMA

    ajuste = ARIMA(serie.to_numpy(float), order=(1, 1, 0), trend="t",
                   exog=frame.dummies_atipicos(serie.index)).fit()
    psi = models.pesos_psi(ajuste.arparams, ajuste.maparams, 3)
    nivel = p.varianza[0] * np.cumsum(np.cumsum(psi) ** 2)
    assert np.allclose(nivel, p.varianza, rtol=1e-3)
    # con φ > 0 el nivel acumula más que el crecimiento de un año a partir del segundo paso
    assert p.varianza[1] > 2 * p.varianza_crecimiento[1]


def test_combinar_suma_el_desacuerdo_en_el_crecimiento_de_cada_anio():
    """Dos modelos que coinciden en el nivel de 2026 y discrepan en 2027 discrepan en el crecimiento de 2027."""
    a = models.Pronostico(np.array([1.0, 1.1]), np.array([0.01, 0.02]), np.array([0.01, 0.01]))
    b = models.Pronostico(np.array([1.0, 1.3]), np.array([0.01, 0.02]), np.array([0.01, 0.01]))
    c = models.combinar({"a": a, "b": b})
    assert c.varianza_crecimiento[0] == pytest.approx(0.01)
    assert c.varianza_crecimiento[1] == pytest.approx(0.01 + 0.1 ** 2)
    sin = models.Pronostico(np.array([1.0, 1.2]), np.array([0.01, 0.02]))
    assert models.combinar({"a": a, "sin": sin}).varianza_crecimiento is None
    assert np.isnan(sin.ancho_crecimiento()).all(), "sin varianza del crecimiento no hay ancho que inventar"


# ------------------------------------------------------------------ vigencia del ancla (A3)

def test_el_ancla_vieja_avisa_y_lo_deja_escrito(tmp_path, monkeypatch):
    from datetime import date

    from iif.forecast import anchor

    viejo = reconcile.Ancla("prueba", "2025-05-15", {2026: 2.6})
    estado = anchor.vigencia(viejo, hoy=date(2026, 9, 23))
    assert estado["vencida"] and 16 < estado["antiguedad_meses"] < 16.5
    assert "config/forecast.yaml" in estado["aviso"]
    nuevo = anchor.vigencia(reconcile.Ancla("prueba", "2026-08-31", {2026: 2.6}), hoy=date(2026, 9, 23))
    assert not nuevo["vencida"] and nuevo["aviso"] is None
    assert anchor.vigencia(reconcile.Ancla("prueba", "desconocida", {}))["vencida"]

    ruta = tmp_path / "forecast.yaml"
    ruta.write_text("anclas:\n  central:\n    fuente: prueba\n    fecha_corte: '2020-01-31'\n"
                    "    crecimiento: {2026: 2.0, 2027: 2.0, 2028: 2.0}\n", encoding="utf-8")
    monkeypatch.setattr(anchor, "CONFIG_FORECAST", ruta)
    with pytest.warns(anchor.AnclaVencida, match="meses de antigüedad"):
        ancla = anchor.cargar([2026, 2027, 2028], sin_red=True)
    assert ancla.fuente == "prueba"


# ------------------------------------------------------------------ escenario y reconciliación (A10)

def test_el_desplazamiento_de_la_reconciliacion_se_publica_con_su_rango():
    from iif.forecast import run

    sin = pd.DataFrame({"01": [3.0, 3.1], "02": [1.0, 0.5]}, index=pd.Index([2026, 2027], name="anio"))
    rec = sin - pd.DataFrame({"01": [0.80, 0.70], "02": [0.86, 0.72]}, index=sin.index)
    d = run.desplazamiento_de_la_reconciliacion(sin, rec, {"01": "Uno", "02": "Dos"})
    assert d["2026"]["minimo_pp"] == pytest.approx(-0.86)
    assert d["2026"]["rango_pp"] == pytest.approx(0.06)
    assert d["2026"]["departamento_minimo"] == "Dos"
    texto = run.lectura_del_escenario({"fuente": "FMI", "fecha_corte": "2025-05-15",
                                       "antiguedad_meses": 16.3, "vencida": True}, d)
    assert texto.startswith("Escenario condicional al ancla")
    assert "16 meses" in texto and "casi lo mismo" in texto and "tablas de posiciones" in texto


def test_la_lectura_lleva_la_cobertura_del_intervalo():
    from iif.forecast.run import lectura_de_la_puerta

    v = backtest.Veredicto("combinacion", 3.4, 1.0, 38.5539, 0.287, 264, True,
                           origenes_ganados=3, n_origenes=8, mejor_origen=2021,
                           ganancia_sin_mejor_origen_pct=8.29)
    assert "cubrió el 81 %" in lectura_de_la_puerta(v, 0.8144)
    assert "cubrió" not in lectura_de_la_puerta(v)


# ------------------------------------------------------------------ cifras publicadas (R-09)

RESULTADOS = config.DATA_PROCESSED / "forecast" / "resultados.json"

# Las cifras que cita la adenda de 2026-09-23 de ADR-022, en pp al 80 %: (crecimiento 2026,
# crecimiento 2028, nivel 2028). A un año el ancho del nivel y el del crecimiento coinciden.
ANCHOS_ADR_022 = {
    "91": (4.3, 4.5, 8.5),     # Amazonas
    "11": (4.9, 5.1, 9.9),     # Bogotá
    "76": (5.2, 5.9, 11.8),    # Valle del Cauca
    "81": (11.6, 11.9, 23.0),  # Arauca
    "27": (13.9, 16.2, 33.7),  # Chocó
    "50": (17.0, 19.2, 40.2),  # Meta
    "86": (18.7, 20.0, 40.5),  # Putumayo
}
MEDIANAS_ADR_022 = (7.4, 7.7, 14.8)


@pytest.mark.data
@pytest.mark.skipif(not RESULTADOS.exists(), reason="sin resultados.json; corre `uv run iif forecast`")
def test_las_cifras_de_adr_022_cuadran_con_resultados_json():
    """La tabla de ADR-022 dejó de cuadrar con la salida sin que nada fallara (informe 02, A2)."""
    import json

    r = json.loads(RESULTADOS.read_text(encoding="utf-8"))
    deps = r["departamentos"]
    for cod, (c26, c28, n28) in ANCHOS_ADR_022.items():
        crec, nivel = deps[cod]["intervalo_ancho_crecimiento_pp"], deps[cod]["intervalo_ancho_nivel_pp"]
        assert round(crec[0], 1) == c26, (cod, crec)
        assert round(crec[2], 1) == c28, (cod, crec)
        assert round(nivel[2], 1) == n28, (cod, nivel)
        assert nivel[0] == pytest.approx(crec[0], abs=1e-6)
    med = [float(np.median([d[k][i] for d in deps.values()]))
           for k, i in (("intervalo_ancho_crecimiento_pp", 0), ("intervalo_ancho_crecimiento_pp", 2),
                        ("intervalo_ancho_nivel_pp", 2))]
    assert tuple(round(m, 1) for m in med) == MEDIANAS_ADR_022
    # La cobertura, el ancla y el desplazamiento que citan la adenda y el informe final.
    puerta = r["puerta_de_calidad"]
    assert round(puerta["cobertura_intervalo_empirica"], 2) == 0.81
    comb = next(c for c in r["backtest"]["cobertura_intervalo"] if c["modelo"] == "combinacion")
    assert comb["cobertura_empirica"] == puerta["cobertura_intervalo_empirica"]
    assert "antiguedad_meses" in r["ancla"]
    d26 = r["reconciliacion"]["desplazamiento_crecimiento_pp"]["2026"]
    assert round(d26["minimo_pp"], 2) == -0.86 and round(d26["maximo_pp"], 2) == -0.82
    assert d26["rango_pp"] < 0.1, "el ancla desplaza a todos casi lo mismo"
    assert r["escenario"]["lectura"].startswith("Escenario condicional al ancla")
    sueltas = [c["cobertura_empirica"] for c in r["backtest"]["cobertura_intervalo"]
               if c["modelo"] not in {"combinacion", "ingenuo"}]
    assert (round(min(sueltas), 2), round(max(sueltas), 2)) == (0.64, 0.77)


@pytest.mark.data
@pytest.mark.skipif(not RESULTADOS.exists(), reason="sin resultados.json; corre `uv run iif forecast`")
def test_el_tamano_no_predice_el_ancho_vigente(marco):
    """ADR-022, adenda: el ancho a un año varía 4,4 veces y el peso en el PIB no lo predice (ρ = −0,42)."""
    import json

    deps = json.loads(RESULTADOS.read_text(encoding="utf-8"))["departamentos"]
    ancho = pd.Series({c: v["intervalo_ancho_crecimiento_pp"][0] for c, v in deps.items()})
    peso = marco.pib_nivel.iloc[-1] / marco.pib_nivel.iloc[-1].sum()
    assert round(ancho.max() / ancho.min(), 1) == 4.4
    assert round(peso.corr(ancho.reindex(peso.index), method="spearman"), 2) == -0.42
