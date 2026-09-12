"""La potencia se prueba donde la respuesta se conoce de antemano: en aritmética y en paneles construidos.

Un módulo que existe para decir qué efectos descarta un diseño tiene que estar bien, porque su salida se
publica como la afirmación principal del trabajo (ADR-018). Las pruebas de aquí fijan tres cosas: que el
MDE es la fórmula que dice ser, que el TOST rechaza cuando debe y no cuando no debe, y que la escala del
regresor separa de verdad la variación que los efectos fijos dejan en pie.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from iif.econ.power import escala_del_regresor, grados_de_libertad, mde, resumen, tost


def test_el_mde_es_la_suma_de_los_dos_valores_criticos():
    # 1,959964 del contraste a dos colas al 5 % más 0,841621 de la potencia del 80 % a una cola.
    assert mde(0.01) == pytest.approx(0.02801585, abs=1e-7)
    assert mde(0.01, potencia=0.50) == pytest.approx(0.01959964, abs=1e-7)


def test_el_mde_crece_con_la_potencia_y_con_el_error_estandar():
    assert mde(0.01, potencia=0.9) > mde(0.01, potencia=0.8) > mde(0.01, potencia=0.5)
    assert mde(0.02) == pytest.approx(2 * mde(0.01), rel=1e-12)


def test_el_mde_no_inventa_un_numero_cuando_no_hay_error_estandar():
    assert np.isnan(mde(0.0))
    assert np.isnan(mde(float("nan")))


def test_el_tost_declara_equivalencia_solo_cuando_el_margen_es_mayor_que_la_imprecision():
    # Coeficiente nulo y muy preciso: cualquier margen razonable queda demostrado.
    holgado = tost(coef=0.0, se=0.001, margen=0.01, gl=200)
    assert holgado["equivale"] and holgado["p"] < 0.001
    # El mismo coeficiente con un margen más estrecho que su propia imprecisión: no se puede afirmar nada.
    estrecho = tost(coef=0.0, se=0.01, margen=0.001, gl=200)
    assert not estrecho["equivale"]


def test_el_tost_no_declara_equivalencia_con_un_coeficiente_grande():
    """Un efecto claramente mayor que el margen no es equivalente por mucha precisión que tenga."""
    lejos = tost(coef=0.05, se=0.001, margen=0.01, gl=200)
    assert not lejos["equivale"]


def test_el_tost_es_simetrico_en_el_signo():
    a = tost(coef=0.004, se=0.002, margen=0.01, gl=100)
    b = tost(coef=-0.004, se=0.002, margen=0.01, gl=100)
    assert a["p"] == pytest.approx(b["p"], rel=1e-12)


def test_los_grados_de_libertad_descuentan_los_efectos_fijos():
    # 228 filas, 33 unidades, 7 periodos, 3 regresores: 228 - (33 + 7 - 1) - 3 = 186.
    assert grados_de_libertad(228, 33, 7, 3) == 186


def _panel(*, n=30, t=8, ruido=0.4, semilla=3):
    """Panel donde el regresor es efecto de unidad + efecto de año + un ruido de tamaño conocido.

    La variación que sobrevive a los efectos fijos de dos vías es exactamente ese ruido, así que la
    desviación identificante tiene que acercarse a `ruido` y la bruta tiene que ser mucho mayor.
    """
    rng = np.random.default_rng(semilla)
    alfa, gamma = rng.normal(0, 2.0, n), rng.normal(0, 2.0, t)
    filas = []
    for i in range(n):
        for k in range(t):
            filas.append(
                {
                    "dpto_ccdgo": f"{i:02d}",
                    "anio": 2018 + k,
                    "x": alfa[i] + gamma[k] + rng.normal(0, ruido),
                    "c": rng.normal(),
                }
            )
    return pd.DataFrame(filas)


def test_la_escala_separa_la_variacion_que_los_efectos_fijos_dejan_en_pie():
    df = _panel(ruido=0.4)
    e = escala_del_regresor(df, "x")
    assert e["de_identificante"] == pytest.approx(0.4, abs=0.06), e
    assert e["de_bruta"] > 4 * e["de_identificante"], "casi toda la varianza era unidad y año"
    assert 0 < e["varianza_que_identifica"] < 0.15


def test_la_escala_no_cambia_por_anadir_un_control_ortogonal():
    """El control `c` es ruido independiente: residualizar contra él no puede mover la escala."""
    df = _panel()
    sin = escala_del_regresor(df, "x")["de_identificante"]
    con = escala_del_regresor(df, "x", ["c"])["de_identificante"]
    assert con == pytest.approx(sin, rel=0.05)


def test_el_resumen_traduce_el_coeficiente_a_puntos_porcentuales_por_desviacion():
    """La traducción es coeficiente x desviación identificante x 100, y el resumen tiene que hacerla igual."""
    from iif.econ.panel import two_way_fe

    df = _panel()
    rng = np.random.default_rng(11)
    df["y"] = 0.01 * df["x"] + rng.normal(0, 0.02, len(df))
    est, _ = two_way_fe(df, "y", "x", ["c"])
    r = resumen(est, df, "x", ["c"])
    sd = r["escala_del_regresor"]["de_identificante"]
    assert r["mde"]["potencia_80_pp_por_de"] == pytest.approx(r["mde"]["potencia_80"] * sd * 100, rel=1e-9)
    assert r["intervalo"]["ic95_pp_por_de"][0] < r["intervalo"]["ic95_pp_por_de"][1]
    assert [t["margen_pp_por_de"] for t in r["equivalencia"]] == [0.25, 0.50, 1.00]


def test_un_efecto_verdadero_grande_no_pasa_la_prueba_de_equivalencia():
    """Si el efecto existe y es grande, el TOST con un margen pequeño no puede declararlo equivalente."""
    from iif.econ.panel import two_way_fe

    df = _panel()
    rng = np.random.default_rng(5)
    df["y"] = 0.2 * df["x"] + rng.normal(0, 0.02, len(df))
    est, _ = two_way_fe(df, "y", "x", ["c"])
    r = resumen(est, df, "x", ["c"])
    assert not r["equivalencia"][0]["equivale"], "0,25 pp por desviación no puede cubrir un efecto así"
