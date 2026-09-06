"""Índice de inclusión financiera: normalización, ajuste, pesos implícitos y reproducibilidad (ADR-015)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from iif import config
from iif.index.build import DimensionFit, build_index, fit_dimension, load_contract, normalize_panel


@pytest.fixture(scope="module")
def contrato():
    return load_contract()


def _panel_sintetico(n_unidades=40, anios=(2018, 2019, 2020)):
    """Panel donde la inclusión crece con el tiempo y el tamaño de la unidad es puro ruido de escala."""
    rng = np.random.default_rng(7)
    filas = []
    for u in range(n_unidades):
        poblacion = float(rng.integers(50_000, 5_000_000))
        producto = poblacion * rng.uniform(8, 30) / 1e9  # miles de millones
        nivel = rng.normal(0, 1)
        for i, anio in enumerate(anios):
            intensidad = nivel + 0.4 * i
            filas.append(
                dict(
                    dpto_ccdgo=f"{u:02d}",
                    anio=anio,
                    poblacion_total=poblacion,
                    pib_corriente_mm=producto,
                    nro_corresp_activos=max(poblacion / 10_000 * (5 + intensidad), 1),
                    nro_total=max(poblacion / 10_000 * (900 + 100 * intensidad), 1),
                    monto_total=max(producto * 1e9 * (0.06 + 0.01 * intensidad), 1),
                    nro_total_cta_ahorros=max(poblacion / 10_000 * (1500 + 200 * intensidad), 1),
                    saldo_total_cta_ahorros=max(producto * 1e9 * (0.12 + 0.02 * intensidad), 1),
                    monto_total_cred_consumo=max(producto * 1e9 * (0.10 + 0.02 * intensidad), 1),
                    monto_total_cred_vivienda=max(producto * 1e9 * (0.03 + 0.01 * intensidad), 1),
                    monto_total_micro=max(producto * 1e9 * (0.02 + 0.005 * intensidad), 1),
                )
            )
    return pd.DataFrame(filas)


UNIDADES = {
    "nro_corresp_activos": "count",
    "nro_total": "count",
    "nro_total_cta_ahorros": "count",
    "monto_total": "cop",
    "saldo_total_cta_ahorros": "cop",
    "monto_total_cred_consumo": "cop",
    "monto_total_cred_vivienda": "cop",
    "monto_total_micro": "cop",
}


def test_contrato_solo_usa_variables_que_existen_en_las_dos_tablas():
    """Toda variable del índice debe estar en dim_variable y existir en ptgf y kx2f (ADR-015, punto 2)."""
    contrato = load_contract()
    dim = pd.read_csv(config.SEEDS_DIR / "dim_variable.csv")
    elegidas = [v["variable_id"] for d in contrato["dimensiones"].values() for v in d["variables"]]
    conocidas = dim.set_index("variable_id")
    faltan = [v for v in elegidas if v not in conocidas.index]
    assert not faltan, f"variables del índice que no existen en dim_variable: {faltan}"
    no_continuas = [v for v in elegidas if conocidas.loc[v, "disponible_en"] != "ambas"]
    assert not no_continuas, f"variables que romperían la serie 2017-2025: {no_continuas}"


def test_normalizacion_elimina_la_escala_de_la_unidad(contrato):
    """El punto 1 del ADR: sin normalizar el índice mediría población. Con normalizar, no."""
    panel = _panel_sintetico()
    crudo = panel[["nro_total", "monto_total_cred_consumo"]].corrwith(panel.poblacion_total)
    assert (crudo > 0.8).all(), (
        f"el panel sintético debe reproducir el problema que se quiere evitar: {crudo.to_dict()}"
    )
    norm = normalize_panel(panel, contrato, UNIDADES)
    tras = norm[["nro_total", "monto_total_cred_consumo"]].corrwith(norm.poblacion_total).abs()
    assert (tras < 0.2).all(), f"la normalización no quitó la escala: {tras.to_dict()}"


def test_pesos_implicitos_nunca_negativos(contrato):
    """La razón de haber cambiado el PCA por pesos iguales (ADR-015, adenda)."""
    res = build_index(_panel_sintetico(), UNIDADES, contract=contrato)
    assert (res.implicitos.peso_estandarizado > 0).all(), res.implicitos.to_dict("records")


def test_pesos_congelados_reproducen_exactamente(contrato):
    panel = _panel_sintetico()
    primero = build_index(panel, UNIDADES, contract=contrato)
    congelados = {d: f.__dict__ for d, f in primero.fits.items()}
    # Añadir un año nuevo no debe mover el índice de los años anteriores.
    extra = panel[panel.anio == 2020].assign(anio=2021)
    segundo = build_index(
        pd.concat([panel, extra], ignore_index=True), UNIDADES, contract=contrato, pesos_congelados=congelados
    )
    antes = primero.scores.set_index(["dpto_ccdgo", "anio"]).iif_compuesto
    despues = segundo.scores.set_index(["dpto_ccdgo", "anio"]).iif_compuesto.loc[antes.index]
    pd.testing.assert_series_equal(antes, despues, check_exact=False, rtol=1e-12)


def test_el_indice_crece_cuando_la_inclusion_crece(contrato):
    """En el panel sintético la intensidad sube 0,4 por año: el índice debe reflejarlo."""
    res = build_index(_panel_sintetico(), UNIDADES, contract=contrato)
    por_anio = res.scores.groupby("anio").iif_compuesto.median()
    assert por_anio.is_monotonic_increasing, por_anio.to_dict()


def test_una_dimension_sin_dato_deja_el_compuesto_nulo(contrato):
    """Un dato ausente no se rellena con cero (R-13): el compuesto queda nulo y se cuenta."""
    panel = _panel_sintetico()
    panel.loc[panel.index[:3], "monto_total_cred_vivienda"] = np.nan
    res = build_index(panel, UNIDADES, contract=contrato)
    assert res.scores.iif_compuesto.isna().sum() == 3
    assert (res.scores.dimensiones_observadas == 2).sum() == 3


def test_fit_exige_observaciones_suficientes(contrato):
    calib = _panel_sintetico(n_unidades=5, anios=(2018,))
    norm = normalize_panel(calib, contrato, UNIDADES)
    with pytest.raises(ValueError, match="observaciones completas"):
        fit_dimension(norm, "uso", contrato["dimensiones"]["uso"])


def test_diagnosticos_de_pca_se_calculan_aunque_no_sea_el_metodo(contrato):
    """El KMO se publica siempre: es la evidencia de por qué el PCA no es el método principal."""
    res = build_index(_panel_sintetico(), UNIDADES, contract=contrato)
    for dim in ("uso", "profundidad"):
        assert res.fits[dim].kmo is not None
        assert 0 <= res.fits[dim].kmo <= 1
    assert set(res.correlacion_rangos.columns) == {"iif_compuesto", "iif_pca", "iif_sarma"}


@pytest.mark.data
@pytest.mark.skipif(
    not (config.DATA_PROCESSED / "indice_departamento_anual.parquet").exists(),
    reason="sin data/processed; corre `make index`",
)
def test_indice_publicado_es_coherente():
    d = pd.read_parquet(config.DATA_PROCESSED / "indice_departamento_anual.parquet")
    assert len(d) == 264 and d.anio.between(2018, 2025).all()
    assert d.iif_compuesto.notna().mean() > 0.98
    pesos = pd.read_csv(config.DATA_PROCESSED / "indice_pesos_implicitos.csv")
    assert (pesos.peso_estandarizado > 0).all()
    assert abs(pesos.peso_estandarizado.sum() - 1.0) < 1e-9, "los pesos del compuesto deben sumar 1"


def test_dimension_fit_es_serializable():
    """Los pesos congelados viajan a config/index.yaml, así que deben ser tipos simples."""
    import yaml

    fit = DimensionFit("uso", "pesos_iguales", ["a"], {"a": 1.0}, {"a": 2.0}, {"a": 0.5})
    texto = yaml.safe_dump(fit.__dict__)
    assert yaml.safe_load(texto)["cargas"] == {"a": 0.5}
