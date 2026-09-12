"""Índice de inclusión financiera: normalización, ajuste, pesos implícitos y reproducibilidad (ADR-015)."""

from __future__ import annotations

from pathlib import Path

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
    """En el panel sintético la intensidad sube 0,4 por año: el índice debe reflejarlo.

    Se miran solo los años con índice: con el denominador rezagado (ADR-017) el primer año de cada unidad
    no tiene producto anterior y se queda sin compuesto, que es el comportamiento correcto y lo fija
    `test_el_primer_ano_no_tiene_indice_con_denominador_rezagado`.
    """
    res = build_index(_panel_sintetico(), UNIDADES, contract=contrato)
    por_anio = res.scores.groupby("anio").iif_compuesto.median().dropna()
    assert len(por_anio) >= 2, por_anio.to_dict()
    assert por_anio.is_monotonic_increasing, por_anio.to_dict()


def test_el_primer_ano_no_tiene_indice_con_denominador_rezagado(contrato):
    """Sin producto del año anterior no hay denominador, y un índice sin denominador no se inventa (R-13)."""
    panel = _panel_sintetico()
    res = build_index(panel, UNIDADES, contract={**contrato, "denominador": "rezagado"})
    primer_anio = panel["anio"].min()
    sin_indice = res.scores.loc[res.scores["anio"] == primer_anio, "iif_compuesto"]
    assert sin_indice.isna().all()
    con_contemporaneo = build_index(panel, UNIDADES, contract={**contrato, "denominador": "contemporaneo"})
    assert con_contemporaneo.scores.loc[
        con_contemporaneo.scores["anio"] == primer_anio, "iif_compuesto"
    ].notna().all()


def test_una_dimension_sin_dato_deja_el_compuesto_nulo(contrato):
    """Un dato ausente no se rellena con cero (R-13): el compuesto queda nulo y se cuenta.

    Se cuenta contra la línea de base del mismo panel sin el dato borrado, porque el denominador rezagado
    ya deja nulo el primer año de cada unidad por su cuenta: lo que esta prueba vigila es el efecto del
    dato ausente, no el del denominador.
    """
    panel = _panel_sintetico()
    base = build_index(panel, UNIDADES, contract=contrato).scores
    roto = panel.copy()
    # Se borra el crédito de vivienda del ÚLTIMO año de las tres primeras unidades, que con cualquier
    # denominador tiene índice: así los tres nulos nuevos son atribuibles al dato que falta.
    ultimo = panel["anio"].max()
    objetivo = roto.index[(roto["anio"] == ultimo) & (roto["dpto_ccdgo"].isin(["00", "01", "02"]))]
    assert len(objetivo) == 3
    roto.loc[objetivo, "monto_total_cred_vivienda"] = np.nan
    res = build_index(roto, UNIDADES, contract=contrato)
    assert res.scores.iif_compuesto.isna().sum() == base.iif_compuesto.isna().sum() + 3
    assert (res.scores.loc[objetivo, "dimensiones_observadas"] == 2).all()


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


# --- El denominador de los montos (ADR-017, B-050) ---------------------------------------------------


def _panel_con_producto_que_cae(anios=(2018, 2019, 2020)):
    """Panel donde los numerarios están CONGELADOS y solo se mueve el producto.

    Es el placebo de solo-denominador: un índice construido sobre este panel no contiene ninguna
    información financiera, porque los montos no cambian. Todo lo que se mueva en el índice viene del
    denominador, y por eso sirve para medir cuánto sesgo mete el denominador.
    """
    rng = np.random.default_rng(11)
    filas = []
    for u in range(40):
        poblacion = float(rng.integers(50_000, 5_000_000))
        producto0 = poblacion * rng.uniform(8, 30) / 1e9
        # Cada unidad tiene su propia razón monto/producto: sin esa heterogeneidad la variable normalizada
        # sería idéntica en todas y la calibración no tendría varianza que estandarizar.
        r = {k: v * rng.uniform(0.5, 1.8) for k, v in
             {"monto_total": 0.06, "saldo_total_cta_ahorros": 0.12, "monto_total_cred_consumo": 0.10,
              "monto_total_cred_vivienda": 0.03, "monto_total_micro": 0.02}.items()}
        montos = {k: producto0 * 1e9 * v for k, v in r.items()}
        # El producto sigue un paseo con deriva, como el PIB real: lo que se rezaga tiene que ser una serie
        # PERSISTENTE. Con choques independientes alrededor de una media el rezago introduce una reversión
        # que el PIB no tiene, y el contraste mediría un artefacto del panel sintético y no del método.
        camino, nivel = [], 1.0
        for i in range(len(anios)):
            nivel *= float(np.exp(rng.normal(0.02, 0.05))) if i else 1.0
            camino.append(nivel)
        for i, anio in enumerate(anios):
            factor = camino[i]
            filas.append(
                dict(
                    dpto_ccdgo=f"{u:02d}",
                    anio=anio,
                    poblacion_total=poblacion,
                    pib_corriente_mm=producto0 * factor,
                    nro_corresp_activos=poblacion / 10_000 * 5,
                    nro_total=poblacion / 10_000 * 900,
                    nro_total_cta_ahorros=poblacion / 10_000 * 1500,
                    **montos,
                )
            )
    return pd.DataFrame(filas)


def test_el_denominador_rezagado_usa_el_producto_del_ano_anterior(contrato):
    from iif.index.build import denominador_de_producto

    panel = _panel_sintetico()
    serie, modo = denominador_de_producto(
        panel, {**contrato, "denominador": "rezagado"}, ("dpto_ccdgo", "anio"), "pib_corriente_mm"
    )
    assert modo == "rezagado"
    # El primer año de cada unidad no tiene rezago y se queda sin denominador, que es lo correcto: no se
    # inventa (R-13).
    primera = panel.sort_values(["dpto_ccdgo", "anio"]).groupby("dpto_ccdgo").head(1).index
    assert serie.loc[primera].isna().all()
    ordenado = panel.sort_values(["dpto_ccdgo", "anio"])
    esperado = ordenado.groupby("dpto_ccdgo")["pib_corriente_mm"].shift(1)
    assert serie.reindex(ordenado.index).equals(esperado)


def test_el_denominador_fijo_es_el_del_ano_base_para_toda_la_serie(contrato):
    from iif.index.build import denominador_de_producto

    panel = _panel_sintetico()
    serie, _ = denominador_de_producto(
        panel, {**contrato, "denominador": "fijo"}, ("dpto_ccdgo", "anio"), "pib_corriente_mm"
    )
    base = panel[panel["anio"] == contrato["calibracion"]["anio_desde"]].set_index("dpto_ccdgo")
    for unidad, sub in panel.groupby("dpto_ccdgo"):
        assert serie.loc[sub.index].nunique() == 1
        assert serie.loc[sub.index].iloc[0] == pytest.approx(base.loc[unidad, "pib_corriente_mm"])


def test_un_denominador_desconocido_falla_nombrando_lo_que_admite(contrato):
    from iif.index.build import denominador_de_producto

    with pytest.raises(ValueError, match="contemporaneo"):
        denominador_de_producto(
            _panel_sintetico(), {**contrato, "denominador": "inventado"}, ("dpto_ccdgo", "anio"), "pib_corriente_mm"
        )


def test_el_placebo_de_solo_denominador_pierde_fuerza_al_rezagar(contrato):
    """Con los numerarios congelados, el índice solo se mueve por el denominador.

    Con el producto contemporáneo el índice tiene que saltar cuando el producto cae —que es exactamente la
    correlación mecánica de B-050— y con el rezagado ese salto tiene que ser mucho menor, porque el
    denominador ya no comparte año con el numerador.
    """
    panel = _panel_con_producto_que_cae(anios=(2018, 2019, 2020, 2021, 2022)).sort_values(
        ["dpto_ccdgo", "anio"]
    )
    # El crecimiento del producto del MISMO año, que es lo que la dependiente de la econometría mide.
    panel["g_producto"] = (
        np.log(panel["pib_corriente_mm"]).groupby(panel["dpto_ccdgo"]).diff()
    )

    correlacion = {}
    for modo in ("contemporaneo", "rezagado"):
        res = build_index(panel, UNIDADES, contract={**contrato, "denominador": modo})
        junto = res.scores.merge(panel[["dpto_ccdgo", "anio", "g_producto"]], on=["dpto_ccdgo", "anio"])
        junto = junto.dropna(subset=["iif_compuesto", "g_producto"])
        # Desviación respecto de la media de la unidad: es la variación que un panel con efectos fijos usa.
        dentro_x = junto["iif_compuesto"] - junto.groupby("dpto_ccdgo")["iif_compuesto"].transform("mean")
        dentro_g = junto["g_producto"] - junto.groupby("dpto_ccdgo")["g_producto"].transform("mean")
        correlacion[modo] = float(dentro_x.corr(dentro_g))

    # Con el producto del mismo año en el denominador, un índice SIN contenido financiero correlaciona
    # negativamente con el crecimiento: es la correlación fabricada de B-050, y es la que empujaba el
    # coeficiente de profundidad hacia abajo.
    assert correlacion["contemporaneo"] < -0.3, correlacion
    # Rezagar el denominador quita esa correlación negativa. Lo que se fija aquí es el signo, que es el
    # mecanismo: sobre el panel real la correlación pasa de −0,31 a +0,05, y el placebo deja de ser
    # significativo en cuanto se saca el término de convergencia, con el que es colineal por construcción.
    assert correlacion["rezagado"] > correlacion["contemporaneo"] + 0.3, correlacion
    assert correlacion["rezagado"] > 0, correlacion


def test_el_denominador_fijo_deja_al_placebo_sin_variacion_dentro_de_la_unidad(contrato):
    """Con numeradores y denominador congelados no queda nada que varíe: el sesgo es imposible, no pequeño.

    Es la propiedad que hace del denominador fijo la única alternativa inmune, y también su coste: un
    índice cuyo denominador no se mueve deja de medir profundidad relativa al tamaño actual de la economía
    (ADR-017, alternativas consideradas).
    """
    panel = _panel_con_producto_que_cae(anios=(2018, 2019, 2020, 2021, 2022))
    res = build_index(panel, UNIDADES, contract={**contrato, "denominador": "fijo"})
    scores = res.scores.dropna(subset=["iif_compuesto"])
    dentro = scores.groupby("dpto_ccdgo")["iif_compuesto"].std(ddof=0)
    assert float(dentro.max()) < 1e-9, dentro.describe().to_dict()


def test_recalibrar_vuelve_a_estimar_los_pesos(monkeypatch, contrato):
    """`--recalibrar` tiene que entrar por el camino que estima, no por el que reutiliza (B-053)."""
    from iif.index import run as index_run

    recibido = []

    def falso_build_level(nivel, *, db=None, contract=None, congelados=None):
        recibido.append((nivel, congelados))
        panel = _panel_sintetico()
        return panel, build_index(panel, UNIDADES, contract=contract, pesos_congelados=congelados)

    monkeypatch.setattr(index_run, "build_level", falso_build_level)
    # Solo el nivel departamental: el municipal exige otras claves y aquí no aporta nada al contraste.
    monkeypatch.setattr(index_run, "NIVELES", {"departamento": index_run.NIVELES["departamento"]})
    # Un contrato que SÍ trae pesos congelados: es el caso en el que el fallo se manifestaba.
    congelados_viejos = load_contract().get("pesos_congelados")
    assert congelados_viejos, "el contrato real debe traer pesos congelados para que la prueba tenga sentido"
    monkeypatch.setattr(
        index_run, "load_contract", lambda: {**contrato, "pesos_congelados": congelados_viejos}
    )

    import shutil
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        # El contrato se reescribe en una copia: recalibrar es una decisión de valor y una prueba no la toma.
        destino = Path(tmp) / "config"
        destino.mkdir()
        shutil.copy(config.CONFIG_DIR / "index.yaml", destino / "index.yaml")
        monkeypatch.setattr(index_run.config, "CONFIG_DIR", destino)
        index_run.run(recalibrar=True, out_dir=Path(tmp))
        reescrito = load_contract(destino / "index.yaml")

    assert recibido[0][1] is None, "la primera pasada de una recalibracion no puede llevar los pesos viejos"
    # Y el efecto observable: los pesos escritos son los reestimados sobre el panel, no los de entrada.
    medias_viejas = congelados_viejos["uso"]["media"]
    medias_nuevas = reescrito["pesos_congelados"]["uso"]["media"]
    assert medias_nuevas != medias_viejas, "recalibrar tiene que cambiar los pesos que escribe"

