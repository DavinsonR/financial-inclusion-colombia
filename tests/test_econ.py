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


# --- Lo que la auditoria de septiembre de 2026 dejo fijado (B-048, B-049, B-054) ---------------------


def _panel_espacial(*, n=24, t=7, semilla=17):
    """Panel en fila donde la dependiente hereda del regresor toda su estructura espacial.

    El regresor es suave en el espacio —cada unidad se parece a su vecina— y la dependiente es ese regresor
    mas ruido independiente. Entonces el crecimiento CRUDO tiene dependencia espacial y los residuos del
    modelo que incluye el regresor no la tienen: es exactamente la distincion que B-048 confundio.
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
    """R-09 sobre la prosa: el regresor que corre y el que el texto describe son el mismo (B-049)."""
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
    nube salia demasiado estrecha (B-054).
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
    """El termino de convergencia se estima en cada corrida y hasta ahora se tiraba (B-051)."""
    df = panel_sintetico(beta=0.02, n=33, t=8)
    est, _ = two_way_fe(df, "y", "x", ["c"])
    assert set(est.coeficientes) >= {"x", "c", "const"}
    assert est.coeficientes["x"]["coef"] == pytest.approx(est.coef, rel=1e-12)
    assert est.coeficientes["x"]["p"] == pytest.approx(est.p, rel=1e-12)

