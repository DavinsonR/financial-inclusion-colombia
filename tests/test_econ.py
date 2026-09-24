"""La econometría se prueba donde la verdad se conoce: en paneles sintéticos.

Cada prueba construye un panel con una estructura sabida —un efecto real, una tendencia común que se
disfraza de efecto, dependencia transversal, dependencia espacial— y comprueba que el estimador o la prueba
encuentran exactamente eso. Sin esto, un resultado nulo sobre los datos reales no distingue entre "no hay
efecto" y "el código no lo vería aunque lo hubiera".
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from iif import config
from iif.econ import designs, diagnostics, robustness
from iif.econ.panel import pooled_entity_only, two_way_fe


def panel_sintetico(
    *,
    n: int = 33,
    t: int = 8,
    beta: float = 0.02,
    tendencia_comun: float = 0.0,
    factor_comun: float = 0.0,
    semilla: int = 7,
) -> pd.DataFrame:
    """Panel con efecto conocido y, a elección, una tendencia nacional que suba x e y a la vez."""
    rng = np.random.default_rng(semilla)
    filas = []
    alfa = rng.normal(0, 0.02, n)
    cargas = rng.normal(1, 0.3, n)
    factor = rng.normal(0, 1, t)
    for i in range(n):
        for k in range(t):
            x = rng.normal(0, 1) + tendencia_comun * k
            e = rng.normal(0, 0.03) + factor_comun * cargas[i] * factor[k]
            y = alfa[i] + beta * x + tendencia_comun * 0.01 * k + e
            filas.append(
                {
                    "dpto_ccdgo": f"{i:02d}",
                    "region": "R",
                    "departamento": f"u{i}",
                    "anio": 2018 + k,
                    "y": y,
                    "x": x,
                    "c": rng.normal(),
                }
            )
    return pd.DataFrame(filas)


def test_two_way_fe_recupera_el_efecto_verdadero():
    df = panel_sintetico(beta=0.02, n=60, t=10)
    est, _ = two_way_fe(df, "y", "x", ["c"])
    assert est.coef == pytest.approx(0.02, abs=0.004)
    assert est.n == 600 and est.unidades == 60 and est.periodos == 10


def test_los_efectos_de_tiempo_quitan_la_tendencia_comun():
    """Sin efecto real, una tendencia que sube x e y a la vez fabrica un coeficiente; el efecto de tiempo lo quita."""
    df = panel_sintetico(beta=0.0, tendencia_comun=0.5, n=40, t=8)
    solo_entidad, _ = pooled_entity_only(df, "y", "x", ["c"])
    dos_vias, _ = two_way_fe(df, "y", "x", ["c"])
    assert abs(solo_entidad.coef) > 0.004, (
        "la tendencia comun tiene que parecer un efecto sin efectos de tiempo"
    )
    assert abs(dos_vias.coef) < 0.004, "con efectos de tiempo el falso efecto desaparece"


def _residuos_anchos(res):
    r = res.resids.unstack(level=0)
    r.index = np.asarray(r.index)
    return r


def test_pesaran_cd_detecta_el_factor_comun_y_los_efectos_de_tiempo_lo_atenuan():
    """CD mide la correlacion media entre unidades: la ve cuando el factor carga con el mismo signo en
    todas, y el efecto de tiempo absorbe justo esa parte. Con cargas de media cero CD tiene poca potencia,
    que es una propiedad de la prueba y no un defecto del codigo."""
    independiente = panel_sintetico(beta=0.0, n=33, t=8)
    _, res_i = two_way_fe(independiente, "y", "x")
    cd_i = diagnostics.pesaran_cd(_residuos_anchos(res_i))
    assert abs(cd_i["estadistico"]) < 2.5

    con_factor = panel_sintetico(beta=0.0, factor_comun=0.08, n=33, t=8)
    _, sin_tiempo = pooled_entity_only(con_factor, "y", "x")
    _, con_tiempo = two_way_fe(con_factor, "y", "x")
    cd_sin = diagnostics.pesaran_cd(_residuos_anchos(sin_tiempo))
    cd_con = diagnostics.pesaran_cd(_residuos_anchos(con_tiempo))
    assert cd_sin["estadistico"] > 5, "sin efectos de tiempo el factor comun se ve de lejos"
    assert abs(cd_con["estadistico"]) < cd_sin["estadistico"], "el efecto de tiempo absorbe la parte comun"


def test_wild_cluster_bootstrap_coincide_con_el_estimador():
    df = panel_sintetico(beta=0.0, n=33, t=8)
    df = df.drop(index=[3, 40, 100]).reset_index(drop=True)  # desbalanceado a proposito
    est, _ = two_way_fe(df, "y", "x", ["c"])
    w = robustness.wild_cluster_bootstrap(df, "y", "x", ["c"], replicas=99)
    assert w["coef"] == pytest.approx(est.coef, abs=1e-8), (
        "el desmediado iterativo debe reproducir el coeficiente"
    )
    assert w["clusteres"] == 33


def test_wild_cluster_bootstrap_tiene_el_tamano_nominal_bajo_la_nula():
    """Un solo panel bajo la nula rechaza al 5 % una de cada veinte veces por definicion; el tamano se
    mide sobre muchos paneles, no sobre uno."""
    rechazos = 0
    paneles = 20
    for semilla in range(paneles):
        df = panel_sintetico(beta=0.0, n=33, t=8, semilla=100 + semilla)
        w = robustness.wild_cluster_bootstrap(df, "y", "x", ["c"], replicas=199, semilla=semilla)
        rechazos += w["p_bootstrap"] < 0.05
    assert rechazos / paneles <= 0.2, f"rechaza {rechazos} de {paneles} bajo la nula"


def test_wild_cluster_bootstrap_rechaza_con_efecto_grande():
    df = panel_sintetico(beta=0.05, n=33, t=8)
    w = robustness.wild_cluster_bootstrap(df, "y", "x", ["c"], replicas=199)
    assert w["p_bootstrap"] < 0.05


def test_placebo_por_permutacion_situa_el_efecto_real_fuera_de_la_nube():
    df = panel_sintetico(beta=0.05, n=33, t=8)
    p = robustness.placebo_permutacion(df, "y", "x", ["c"], replicas=59)
    assert p["p_placebo"] < 0.05
    assert abs(p["media_placebos"]) < abs(p["coef_verdadero"])


def test_moran_reconoce_un_patron_espacial_y_uno_aleatorio():
    # una fila de 20 unidades con vecinos a izquierda y derecha
    unidades = [f"{i:02d}" for i in range(20)]
    vecinos = {u: [] for u in unidades}
    for i in range(19):
        vecinos[unidades[i]].append(unidades[i + 1])
        vecinos[unidades[i + 1]].append(unidades[i])
    W = diagnostics.matriz_pesos(unidades, vecinos)
    suave = np.sin(np.linspace(0, np.pi, 20))
    m_suave = diagnostics.moran_i(suave, W, permutaciones=299)
    assert m_suave["I"] > 0.5 and m_suave["p"] < 0.05
    rng = np.random.default_rng(3)
    m_ruido = diagnostics.moran_i(rng.normal(size=20), W, permutaciones=299)
    assert m_ruido["p"] > 0.05


def test_los_vecinos_del_topojson_son_los_de_la_geografia():
    ruta = config.REPO_ROOT / "atlas" / "data" / "geo_departamentos.json"
    if not ruta.exists():
        pytest.skip("sin geometria exportada")
    vecinos = diagnostics.vecinos_desde_topojson(ruta)
    assert "25" in vecinos["11"], "Bogota toca a Cundinamarca"
    assert "11" in vecinos["25"]
    assert vecinos["88"] == [], "el archipielago no toca a nadie"
    assert len(vecinos["05"]) >= 5, "Antioquia tiene muchos vecinos"
    # la relacion es simetrica en todos los casos
    for a, vs in vecinos.items():
        for b in vs:
            assert a in vecinos[b]


def test_cips_rechaza_una_serie_estacionaria_y_no_una_caminata():
    rng = np.random.default_rng(11)
    n, t = 33, 12
    estacionaria = pd.DataFrame({f"{i:02d}": rng.normal(size=t) for i in range(n)})
    caminata = pd.DataFrame({f"{i:02d}": np.cumsum(rng.normal(size=t)) for i in range(n)})
    c_e = diagnostics.cips(estacionaria)["cips"]
    c_c = diagnostics.cips(caminata)["cips"]
    assert c_e < c_c, "la serie estacionaria tiene el estadistico mas negativo"


def test_shift_share_y_estudio_de_eventos_corren_sobre_el_marco():
    df = panel_sintetico(beta=0.02, n=33, t=8)
    exposicion = designs.exposicion_inicial(df, "x", 2018)
    est, datos = designs.shift_share(df[df["anio"] > 2018], "y", "x", exposicion, ["c"])
    assert est.n == len(datos)
    eventos = designs.event_study(df[df["anio"] > 2018], "y", "x", exposicion, anio_evento=2020)
    assert set(eventos["k"]) == {-1, 0, 1, 2, 3, 4, 5}
    assert bool(eventos.loc[eventos["k"] == -1, "referencia"].iloc[0])


def test_cce_absorbe_un_factor_comun_con_cargas_heterogeneas():
    """Un factor con cargas distintas por unidad contamina el two-way FE y no el CCE."""
    rng = np.random.default_rng(5)
    n, t = 33, 8
    factor = np.cumsum(rng.normal(size=t))
    cargas_y = rng.normal(1, 0.5, n)
    cargas_x = rng.normal(1, 0.5, n)
    filas = []
    for i in range(n):
        for k in range(t):
            x = cargas_x[i] * factor[k] + rng.normal()
            y = 0.0 * x + cargas_y[i] * factor[k] + rng.normal(0, 0.3)
            filas.append(
                {
                    "dpto_ccdgo": f"{i:02d}",
                    "region": "R",
                    "departamento": f"u{i}",
                    "anio": 2018 + k,
                    "y": y,
                    "x": x,
                }
            )
    df = pd.DataFrame(filas)
    cce, _ = designs.cce_pooled(df, "y", "x")
    assert abs(cce.coef) < 0.1


def test_los_resultados_publicados_son_los_del_archivo():
    """R-09: si el JSON existe, tiene la forma que la pagina lee."""
    ruta = config.REPO_ROOT / "data" / "processed" / "econ" / "resultados.json"
    if not ruta.exists():
        pytest.skip("sin resultados generados")
    res = json.loads(ruta.read_text(encoding="utf-8"))
    for clave in (
        "especificacion",
        "principales",
        "dimensiones",
        "disenos",
        "diagnosticos",
        "robustez",
        "estudio_eventos",
    ):
        assert clave in res
    assert res["especificacion"]["unidades"] == 33
    assert res["robustez"]["wild_cluster_bootstrap"]["replicas"] >= 499


# --- Lo que la auditoria de septiembre de 2026 dejo fijado (B-068, B-069, B-074) ---------------------


def _panel_espacial(*, n=24, t=7, semilla=17):
    """Panel en fila donde la dependiente hereda del regresor toda su estructura espacial.

    El regresor es suave en el espacio —cada unidad se parece a su vecina— y la dependiente es ese regresor
    mas ruido independiente. Entonces el crecimiento CRUDO tiene dependencia espacial y los residuos del
    modelo que incluye el regresor no la tienen: es exactamente la distincion que B-068 confundio.
    """
    rng = np.random.default_rng(semilla)
    x_espacial = np.sin(np.linspace(0, 2 * np.pi, n))
    filas = []
    for i in range(n):
        for k in range(t):
            x = x_espacial[i] + rng.normal(0, 0.15)
            filas.append(
                {
                    "dpto_ccdgo": f"{i:02d}",
                    "departamento": f"u{i}",
                    "region": "R",
                    "anio": 2018 + k,
                    "x": x,
                    "y": 0.05 * x + rng.normal(0, 0.02),
                }
            )
    unidades = [f"{i:02d}" for i in range(n)]
    vecinos = {u: [] for u in unidades}
    for i in range(n - 1):
        vecinos[unidades[i]].append(unidades[i + 1])
        vecinos[unidades[i + 1]].append(unidades[i])
    return pd.DataFrame(filas), unidades, vecinos


def test_moran_se_mide_sobre_residuos_y_no_sobre_la_dependiente():
    """La dependiente cruda y los residuos dan respuestas distintas, y solo una responde a la pregunta.

    La pregunta de la bateria no es si los vecinos crecen parecido —lo hacen— sino si al modelo le queda
    dependencia espacial sin explicar. Aqui el regresor explica toda la estructura, asi que el Moran de la
    dependiente tiene que ser significativo y el de los residuos no.
    """
    df, unidades, vecinos = _panel_espacial()
    W = diagnostics.matriz_pesos(unidades, vecinos)
    _, res = two_way_fe(df, "y", "x")
    resid = res.resids.reset_index()
    resid.columns = ["dpto_ccdgo", "anio", "e"]

    anio = int(df["anio"].median())
    crudo = diagnostics.moran_i(
        df[df.anio == anio].set_index("dpto_ccdgo").reindex(unidades)["y"].to_numpy(), W, permutaciones=499
    )
    residual = diagnostics.moran_i(
        resid[resid.anio == anio].set_index("dpto_ccdgo").reindex(unidades)["e"].to_numpy(),
        W,
        permutaciones=499,
    )
    assert crudo["I"] > 0.4 and crudo["p"] < 0.05, crudo
    assert residual["p"] > 0.05, residual
    assert residual["I"] < crudo["I"], (crudo, residual)


def test_la_especificacion_publicada_declara_si_el_indice_va_rezagado():
    """R-09 sobre la prosa: el regresor que corre y el que el texto describe son el mismo (B-069)."""
    from iif.econ import run as econ_run

    esperado = f"{econ_run.INDICE}_rezago" if econ_run.REZAGO_INDICE else econ_run.INDICE
    assert econ_run.X == esperado

    ruta = config.REPO_ROOT / "data" / "processed" / "econ" / "resultados.json"
    if not ruta.exists():
        pytest.skip("sin resultados generados")
    publicado = json.loads(ruta.read_text(encoding="utf-8"))["especificacion"]["regresor"]
    assert publicado == econ_run.X, (
        f"el JSON publica {publicado!r} y la especificacion corre {econ_run.X!r}"
    )


def _panel_con_persistencia(*, n=33, t=8, rho=0.92, semilla=4):
    """Panel bajo la nula donde el regresor es persistente dentro de cada unidad.

    La persistencia es justo lo que el placebo antiguo destruia al barajar dentro del anio, y por eso su
    nube salia demasiado estrecha (B-074).
    """
    rng = np.random.default_rng(semilla)
    filas = []
    for i in range(n):
        x = 0.0
        for k in range(t):
            x = rho * x + rng.normal(0, 1)
            filas.append(
                {
                    "dpto_ccdgo": f"{i:02d}",
                    "departamento": f"u{i}",
                    "region": "R",
                    "anio": 2018 + k,
                    "x": x,
                    "y": rng.normal(0, 0.03),  # nula: el regresor no explica nada
                }
            )
    return pd.DataFrame(filas)


def test_el_placebo_por_trayectoria_concuerda_con_el_error_agrupado():
    """La nube del placebo debe parecerse al error estandar que el estimador reporta.

    Si la nube es mucho mas estrecha, el placebo rechaza donde el estimador no rechaza, que es lo que
    pasaba barajando dentro del anio. Permutar la trayectoria completa conserva la estructura serial y
    devuelve una nube del orden del error agrupado.
    """
    df = _panel_con_persistencia()
    est, _ = two_way_fe(df, "y", "x")

    trayectoria = robustness.placebo_permutacion(df, "y", "x", replicas=199, modo="trayectoria")
    dentro_anio = robustness.placebo_permutacion(df, "y", "x", replicas=199, modo="dentro_del_anio")

    assert trayectoria["modo"] == "trayectoria"
    assert trayectoria["de_placebos"] == pytest.approx(est.se, rel=0.5), (trayectoria["de_placebos"], est.se)
    # La nube de dentro-del-anio es sistematicamente mas estrecha porque destruye la persistencia. Sobre
    # el panel real la razon es 0,33 (0,00177 contra 0,00542); aqui el margen es menor porque ocho anios
    # de un AR(1) sintetico tienen menos estructura serial que el indice real.
    assert dentro_anio["de_placebos"] < 0.85 * trayectoria["de_placebos"], (
        dentro_anio["de_placebos"],
        trayectoria["de_placebos"],
    )


def test_el_placebo_rechaza_un_modo_que_no_existe():
    df = _panel_con_persistencia(n=10, t=5)
    with pytest.raises(ValueError, match="modo de placebo"):
        robustness.placebo_permutacion(df, "y", "x", replicas=5, modo="inventado")


def test_la_estimacion_guarda_todos_los_coeficientes_no_solo_el_de_interes():
    """El termino de convergencia se estima en cada corrida y hasta ahora se tiraba (B-071)."""
    df = panel_sintetico(beta=0.02, n=33, t=8)
    est, _ = two_way_fe(df, "y", "x", ["c"])
    assert set(est.coeficientes) >= {"x", "c", "const"}
    assert est.coeficientes["x"]["coef"] == pytest.approx(est.coef, rel=1e-12)
    assert est.coeficientes["x"]["p"] == pytest.approx(est.p, rel=1e-12)



# --- ADR-024: inferencia agrupada, tendencias previas y los contrastes del referee ---------------------


def _panel_heterocedastico(*, n=33, t=7, semilla=0, beta=0.0):
    """Nula con errores cuya varianza cambia por departamento y crece con el regresor de ese departamento.

    Es el caso en que un error homocedástico se equivoca y el agrupado no: la prueba de tamaño de abajo
    distingue las dos studentizaciones justo aquí.
    """
    rng = np.random.default_rng(semilla)
    escala_x = rng.lognormal(0, 0.8, n)
    filas = []
    for i in range(n):
        choque = rng.normal(0, 0.02)
        for k in range(t):
            x = rng.normal(0, escala_x[i])
            filas.append(
                {
                    "dpto_ccdgo": f"{i:02d}",
                    "departamento": f"u{i}",
                    "region": "R",
                    "anio": 2019 + k,
                    "x": x,
                    "c": rng.normal(),
                    "y": beta * x + choque + rng.normal(0, 0.01) * escala_x[i] * (1 + abs(x)),
                }
            )
    return pd.DataFrame(filas)


def test_el_crve_del_bootstrap_es_el_agrupado_con_su_correccion():
    """El error del bootstrap es el CRVE: el mismo que statsmodels, salvo la corrección de muestra pequeña.

    statsmodels cuenta las ficticias de unidad en K; el CR1 de aquí no (están anidadas en los clústeres,
    como en Stata). La razón de las dos varianzas tiene que ser exactamente la de esas dos correcciones.
    """
    import statsmodels.api as sm

    from iif.econ import inference

    df = _panel_heterocedastico(semilla=3)
    d = inference.diseno(df, "y", ["x", "c"])
    mio = inference.crve(d, [0])
    sm_res = sm.OLS(d.y, d.X).fit(cov_type="cluster", cov_kwds={"groups": d.grupos})
    k_total = np.linalg.matrix_rank(d.X)
    razon = ((d.n - 1) / (d.n - (k_total - d.anidadas))) / ((d.n - 1) / (d.n - k_total))
    assert mio["coef"][0] == pytest.approx(sm_res.params[0], rel=1e-10)
    assert mio["se"][0] ** 2 == pytest.approx(sm_res.bse[0] ** 2 * razon, rel=1e-8)


def test_los_pesos_de_webb_tienen_media_cero_y_varianza_uno():
    from iif.econ import inference

    w = inference.PESOS["webb"]
    assert w.size == 6 and len(set(np.round(np.abs(w), 12))) == 3
    assert w.mean() == pytest.approx(0.0, abs=1e-12)
    assert (w**2).mean() == pytest.approx(1.0, abs=1e-12)


def test_el_bootstrap_agrupado_tiene_el_tamano_nominal_con_heterocedasticidad():
    """Bajo la nula y con varianzas distintas por departamento, rechaza cerca del 5 % con los dos pesos."""
    paneles = 60
    rechazos = {"rademacher": 0, "webb": 0}
    for semilla in range(paneles):
        df = _panel_heterocedastico(semilla=200 + semilla)
        for pesos in rechazos:
            w = robustness.wild_cluster_bootstrap(df, "y", "x", ["c"], replicas=199, semilla=semilla, pesos=pesos)
            rechazos[pesos] += w["p_bootstrap"] < 0.05
    for pesos, r in rechazos.items():
        assert r / paneles <= 0.15, f"{pesos}: rechaza {r} de {paneles} bajo la nula"


def test_el_intervalo_invertido_contiene_al_coeficiente_y_su_borde_es_el_umbral():
    """El IC por inversión es el conjunto de beta0 con p > 0,05: en sus bordes el p cruza 0,05."""
    from iif.econ import inference

    df = panel_sintetico(beta=0.02, n=33, t=7, semilla=21)
    w = robustness.wild_cluster_bootstrap(df, "y", "x", ["c"], replicas=499, invertir=True)
    lo, hi = w["ic95_bootstrap"]
    assert lo < w["coef"] < hi
    est, _ = two_way_fe(df, "y", "x", ["c"])
    assert lo == pytest.approx(est.ic_bajo, abs=2 * est.se)
    assert hi == pytest.approx(est.ic_alto, abs=2 * est.se)
    d = inference.diseno(df, "y", ["x", "c"])
    boot = inference.BootstrapUnCoeficiente(d, 0, replicas=499, semilla=20260907, pesos="rademacher")
    ancho = hi - lo
    assert boot.p_simetrico(hi + 0.02 * ancho) <= 0.05 < boot.p_simetrico(hi - 0.02 * ancho)
    assert boot.p_simetrico(lo - 0.02 * ancho) <= 0.05 < boot.p_simetrico(lo + 0.02 * ancho)


def test_el_tost_bootstrap_y_su_margen_minimo_son_coherentes():
    """Por encima del margen mínimo el TOST declara equivalencia; por debajo, no."""
    from iif.econ import inference

    df = panel_sintetico(beta=0.0, n=33, t=7, semilla=8)
    d = inference.diseno(df, "y", ["x", "c"])
    boot = inference.BootstrapUnCoeficiente(d, 0, replicas=499, semilla=1, pesos="webb")
    m = boot.margen_minimo()
    assert m > abs(boot.coef)
    assert boot.tost(1.05 * m)["equivale"]
    assert not boot.tost(0.95 * m)["equivale"]
    assert not boot.tost(abs(boot.coef) / 2)["equivale"], "un margen menor que el coeficiente no puede pasar"


def test_el_wald_bootstrap_con_una_restriccion_es_la_prueba_simetrica():
    """Con q = 1 el Wald es t al cuadrado: con los mismos pesos, el p bootstrap es el de dos colas."""
    from iif.econ import inference

    df = panel_sintetico(beta=0.01, n=33, t=7, semilla=4)
    d = inference.diseno(df, "y", ["x", "c"])
    wald = inference.wald_bootstrap(d, [0], replicas=299, semilla=5)
    uno = inference.BootstrapUnCoeficiente(d, 0, replicas=299, semilla=5, pesos="rademacher")
    assert wald["p_bootstrap"] == pytest.approx(uno.p_simetrico(0.0), abs=1e-12)
    assert wald["F"] == pytest.approx(uno.t_observado(0.0) ** 2, rel=1e-9)


def _serie_larga(*, tendencia_previa: float, n=33, semilla=2):
    """Crecimiento 2006-2025 con una exposición fija y, a elección, una tendencia previa en los expuestos."""
    rng = np.random.default_rng(semilla)
    exposicion = pd.Series(rng.normal(size=n), index=[f"{i:02d}" for i in range(n)])
    filas = []
    for i, u in enumerate(exposicion.index):
        for a in range(2006, 2026):
            previo = tendencia_previa * exposicion[u] * (a - 2012) / 10 if a < 2019 else 0.0
            filas.append({"dpto_ccdgo": u, "anio": a, "g": previo + rng.normal(0, 0.02) + 0.001 * i})
    return pd.DataFrame(filas), exposicion


def test_las_tendencias_previas_se_detectan_cuando_existen_y_no_cuando_no():
    sin, exp_sin = _serie_larga(tendencia_previa=0.0)
    con, exp_con = _serie_larga(tendencia_previa=0.03)
    r_sin = designs.tendencias_previas(sin, "g", exp_sin, replicas=199)
    r_con = designs.tendencias_previas(con, "g", exp_con, replicas=199)
    assert r_sin["previos"]["q"] == 13 and r_sin["posteriores"]["q"] == 6
    assert r_sin["previos"]["p_bootstrap"] > 0.05
    assert r_con["previos"]["p_bootstrap"] < 0.05 and r_con["previos"]["p_F"] < 0.05
    ref = [f for f in r_sin["coeficientes"] if f["referencia"]]
    assert len(ref) == 1 and ref[0]["anio"] == 2019


def test_una_condicion_inicial_absorbe_la_tendencia_que_ella_misma_produce():
    """Si la pendiente previa es de la urbanización y no de la exposición, meterla dentro la quita."""
    datos, exposicion = _serie_larga(tendencia_previa=0.0, semilla=9)
    rng = np.random.default_rng(1)
    urbana = exposicion * 0.9 + rng.normal(0, 0.3, exposicion.size)
    datos["g"] = datos["g"] + datos["dpto_ccdgo"].map(urbana) * (datos["anio"] - 2015) * 0.004
    sin = designs.tendencias_previas(datos, "g", exposicion, replicas=199)
    con = designs.tendencias_previas(datos, "g", exposicion, controles_iniciales={"urb": urbana}, replicas=199)
    assert sin["previos"]["p_bootstrap"] < 0.05
    assert con["previos"]["p_bootstrap"] > sin["previos"]["p_bootstrap"]


def test_los_pesos_de_aronow_samii_suman_uno_y_premian_la_variacion_dentro():
    from iif.econ.power import pesos_aronow_samii

    df = panel_sintetico(beta=0.0, n=20, t=7, semilla=6)
    df.loc[df["dpto_ccdgo"] == "03", "x"] *= 6  # la unidad con más variación dentro
    w = pesos_aronow_samii(df, "x", ["c"])
    assert w.sum() == pytest.approx(1.0, abs=1e-12)
    assert w.idxmax() == "03"


def test_holm_coincide_con_statsmodels():
    from statsmodels.stats.multitest import multipletests

    from iif.econ.inference import holm

    p = [0.001, 0.04, 0.03, 0.2, 0.012, 0.5]
    assert np.allclose(holm(p), multipletests(p, method="holm")[1])


def test_congelar_numeradores_deja_solo_el_denominador():
    from iif.econ.denominador import congelar_numeradores

    panel = pd.DataFrame(
        {
            "dpto_ccdgo": ["01", "01", "02", "02"],
            "anio": [2018, 2019, 2018, 2019],
            "monto": [10.0, 30.0, 5.0, 7.0],
            "pib": [100.0, 90.0, 50.0, 60.0],
        }
    )
    congelado = congelar_numeradores(panel, ["monto"], 2018)
    assert congelado["monto"].tolist() == [10.0, 10.0, 5.0, 5.0]
    assert congelado["pib"].tolist() == panel["pib"].tolist()


def test_el_diseno_de_exposicion_inicial_conserva_el_alias_viejo():
    assert designs.shift_share is designs.exposicion_por_adopcion
    df = panel_sintetico(beta=0.02, n=33, t=8)
    exposicion = designs.exposicion_inicial(df, "x", 2018)
    est, _ = designs.exposicion_por_adopcion(df[df["anio"] > 2018], "y", "x", exposicion, ["c"])
    assert "exposición inicial" in est.nombre and "shift" not in est.nombre
