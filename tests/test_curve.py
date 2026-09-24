"""La curva de especificación tiene que contar lo que hay, no lo que conviene.

Es la página más fácil de convertir en propaganda: basta elegir los ejes que dan el contraste más vistoso.
Estas pruebas fijan lo contrario —que la rejilla es exhaustiva sobre sus ejes, que no descarta en silencio
y que el contraste que publica es el que los datos producen— sobre paneles donde la respuesta se conoce.
"""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
import pytest

from iif.econ import curve


def _marco(*, beta_comun=0.0, tendencia=0.0, n=33, t=8, semilla=5):
    """Panel con las columnas que la rejilla espera, y una tendencia común opcional.

    Con `tendencia` distinta de cero, el regresor y la dependiente suben los dos con los años sin ninguna
    relación entre unidades: es la correlación espuria que los efectos de tiempo existen para quitar.
    """
    rng = np.random.default_rng(semilla)
    alfa = rng.normal(0, 0.02, n)
    filas = []
    for i in range(n):
        for k in range(t):
            x = rng.normal(0, 1) + tendencia * k
            y = alfa[i] + beta_comun * x + tendencia * 0.01 * k + rng.normal(0, 0.03)
            filas.append(
                {
                    "dpto_ccdgo": f"{i:02d}",
                    "departamento": f"u{i}",
                    "region": "R",
                    "anio": 2018 + k,
                    "crecimiento": y,
                    "iif_compuesto": x,
                    "log_pib_rezago": rng.normal(10, 0.5),
                    "tasa_urbanizacion": rng.uniform(0.3, 0.9),
                }
            )
    df = pd.DataFrame(filas).sort_values(["dpto_ccdgo", "anio"])
    df["iif_compuesto_rezago"] = df.groupby("dpto_ccdgo", sort=False)["iif_compuesto"].shift(1)
    df["d_iif_compuesto"] = df.groupby("dpto_ccdgo", sort=False)["iif_compuesto"].diff()
    for col in ("iif_acceso", "iif_uso", "iif_profundidad", "iif_sensibilidad_pca", "iif_sensibilidad_sarma"):
        df[col] = df["iif_compuesto"] + rng.normal(0, 0.3, len(df))
    return df.reset_index(drop=True)


@pytest.fixture
def rejilla_espuria(monkeypatch):
    """Rejilla sobre un panel sin efecto real pero con una tendencia común fuerte."""
    marco = _marco(beta_comun=0.0, tendencia=0.5)
    monkeypatch.setattr(curve, "load_frame", lambda db=None: marco)
    return curve.estimar_rejilla()


def test_la_rejilla_cubre_el_producto_cartesiano_de_sus_ejes(rejilla_espuria):
    """Si una combinación se cae, se cuenta como no estimable; no desaparece del denominador."""
    esperado = len(curve.REGRESORES) * len(curve.CONTROLES) * len(curve.MUESTRAS) * len(curve.EFECTOS)
    assert len(rejilla_espuria) == esperado, (len(rejilla_espuria), esperado)
    combinaciones = set(
        zip(
            rejilla_espuria["regresor"],
            rejilla_espuria["controles"],
            rejilla_espuria["muestra"],
            rejilla_espuria["efectos"],
            strict=True,
        )
    )
    assert len(combinaciones) == esperado, "hay combinaciones repetidas o faltantes"
    assert combinaciones == set(
        itertools.product(curve.REGRESORES, curve.CONTROLES, curve.MUESTRAS, curve.EFECTOS)
    )


def test_los_efectos_de_tiempo_derrumban_la_proporcion_de_significativas(rejilla_espuria):
    """El contraste que la página publica tiene que aparecer donde la espuriedad es conocida."""
    resumen = curve.resumir(rejilla_espuria)
    sin = resumen["solo entidad"]["fraccion"]
    con = resumen["entidad y tiempo"]["fraccion"]
    assert sin > 0.5, f"sin efectos de tiempo la tendencia comun tiene que fabricar significancia: {sin}"
    # Lo que la pagina afirma es el derrumbe, no un umbral concreto: la proporcion tiene que caer al menos
    # a la mitad. Sobre el panel real cae de 0,61 a 0,06.
    assert con < sin / 2, (con, sin)
    assert con < 0.3, f"con efectos de tiempo casi nada deberia sobrevivir: {con}"


def test_sin_tendencia_comun_ningun_regimen_fabrica_significancia(monkeypatch):
    """El contraste no es un artefacto del método: sin tendencia, las dos columnas son igual de planas."""
    marco = _marco(beta_comun=0.0, tendencia=0.0, semilla=9)
    monkeypatch.setattr(curve, "load_frame", lambda db=None: marco)
    resumen = curve.resumir(curve.estimar_rejilla())
    assert resumen["solo entidad"]["fraccion"] < 0.3
    assert resumen["entidad y tiempo"]["fraccion"] < 0.3


def test_un_efecto_real_sobrevive_a_los_efectos_de_tiempo(monkeypatch):
    """Y al revés: si el efecto es real y no es tendencia, la columna derecha tiene que verlo."""
    marco = _marco(beta_comun=0.05, tendencia=0.0, semilla=3)
    monkeypatch.setattr(curve, "load_frame", lambda db=None: marco)
    rejilla = curve.estimar_rejilla()
    compuesto = rejilla[
        (rejilla["regresor"] == "índice compuesto")
        & (rejilla["efectos"] == "entidad y tiempo")
        & (rejilla["muestra"] == "completa")
    ]
    assert compuesto["significativa"].all(), compuesto[["controles", "coef", "p"]].to_dict("records")


def test_el_coeficiente_en_puntos_porcentuales_usa_la_desviacion_identificante(rejilla_espuria):
    """Los regresores no comparten escala: sin esta traducción, el gráfico compara peras con manzanas."""
    vivas = rejilla_espuria[rejilla_espuria["estimable"]]
    assert (vivas["de_identificante"] > 0).all()
    esperado = vivas["coef"] * vivas["de_identificante"] * 100
    assert np.allclose(vivas["coef_pp"], esperado, atol=1e-3)
    # Y el intervalo traducido conserva el orden.
    assert (vivas["ic_bajo_pp"] <= vivas["coef_pp"] + 1e-9).all()
    assert (vivas["coef_pp"] <= vivas["ic_alto_pp"] + 1e-9).all()


def test_el_resumen_no_esconde_las_no_estimables(monkeypatch):
    """Una especificación que el estimador no resuelve se cuenta, para que el denominador sea honesto."""
    marco = _marco()
    marco["iif_sensibilidad_sarma"] = 1.0  # constante: los efectos de entidad la absorben
    monkeypatch.setattr(curve, "load_frame", lambda db=None: marco)
    salida = curve.run()
    assert salida["no_estimables"] > 0
    assert salida["total"] == len(salida["especificaciones"]) + salida["no_estimables"]
