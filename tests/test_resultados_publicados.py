"""R-09 con dientes: el código actual tiene que reproducir las cifras que el repositorio publica.

Hasta ahora `resultados.json` estaba commiteado y nada comprobaba que la batería lo volviera a producir. La
regla decía que toda cifra publicada traza a una prueba, pero la prueba que existía solo miraba que las
CLAVES del archivo estuvieran, no sus valores: el código y el número podían separarse en silencio (B-052 en
espíritu, y la razón por la que este archivo existe).

Estas pruebas llevan la marca `data` porque necesitan el almacén construido (`make dbt-build`). En CI corren
después de `dbt build`, que es cuando la base existe.
"""

from __future__ import annotations

import json
import math

import pytest

from iif import config

pytestmark = pytest.mark.data

RUTA = config.REPO_ROOT / "data" / "processed" / "econ" / "resultados.json"
BASE_DUCKDB = config.DUCKDB_PATH

# Claves cuyo valor cambia en cada corrida por diseño y que no se comparan.
VOLATILES = {"generado_en"}


@pytest.fixture(scope="module")
def publicado():
    if not RUTA.exists():
        pytest.skip("sin resultados publicados")
    return json.loads(RUTA.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def regenerado():
    if not BASE_DUCKDB.exists():
        pytest.skip(f"sin {BASE_DUCKDB}; corre `make dbt-build`")
    from iif.econ.run import run

    return run()


def _diferencias(a, b, ruta="", tol=1e-6):
    """Compara dos árboles JSON y devuelve las rutas donde difieren más que la tolerancia."""
    if isinstance(a, dict):
        salida = []
        for clave in a:
            if clave in VOLATILES:
                continue
            if clave not in b:
                salida.append((f"{ruta}/{clave}", a[clave], "AUSENTE"))
                continue
            salida += _diferencias(a[clave], b[clave], f"{ruta}/{clave}", tol)
        return salida
    if isinstance(a, list):
        if len(a) != len(b):
            return [(ruta, f"{len(a)} elementos", f"{len(b)} elementos")]
        salida = []
        for i, (x, y) in enumerate(zip(a, b, strict=True)):
            salida += _diferencias(x, y, f"{ruta}[{i}]", tol)
        return salida
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        if a is None or b is None:
            return [] if a == b else [(ruta, a, b)]
        if math.isclose(float(a), float(b), rel_tol=tol, abs_tol=tol):
            return []
        return [(ruta, a, b)]
    return [] if a == b else [(ruta, a, b)]


def test_la_bateria_reproduce_el_json_publicado(publicado, regenerado):
    """Toda cifra del archivo publicado sale de correr el código de hoy sobre el almacén de hoy."""
    difs = _diferencias(publicado, regenerado)
    detalle = "\n".join(f"  {r}: publicado={x!r} recalculado={y!r}" for r, x, y in difs[:20])
    assert not difs, f"{len(difs)} cifras publicadas no se reproducen:\n{detalle}"


def test_la_especificacion_publicada_es_la_que_corre(publicado):
    """Si alguien cambia la especificación y no regenera, esto lo dice antes que un lector."""
    from iif.econ import run as econ_run

    e = publicado["especificacion"]
    assert e["dependiente"] == econ_run.Y
    assert e["regresor"] == econ_run.X
    assert e["controles"] == econ_run.CONTROLES
    assert e["anio_base_exposicion"] == econ_run.ANIO_BASE
    assert e["anio_evento"] == econ_run.ANIO_EVENTO


def test_el_bloque_de_potencia_acompana_al_resultado(publicado):
    """ADR-018: el nulo no se publica sin la cota que lo hace interpretable."""
    p = publicado["potencia"]
    assert p["mde"]["potencia_80"] > 0
    assert p["escala_del_regresor"]["de_identificante"] > 0
    assert p["escala_del_regresor"]["de_identificante"] < p["escala_del_regresor"]["de_bruta"], (
        "los efectos fijos tienen que reducir la variacion del regresor"
    )
    margenes = [t["margen_pp_por_de"] for t in p["equivalencia"]]
    assert margenes == sorted(margenes) and len(margenes) >= 3
    # La equivalencia es monótona: si un margen se demuestra, todos los mayores también.
    demostrados = [t["equivale"] for t in p["equivalencia"]]
    assert demostrados == sorted(demostrados), demostrados


def test_el_moran_publicado_se_mide_sobre_los_residuos(publicado):
    """B-048: la tabla publica los tres objetos y el de los residuos es el que sostiene la afirmación."""
    for fila in publicado["diagnosticos"]["moran_por_anio"]:
        assert {"crecimiento", "residuos_base", "residuos_slx"} <= set(fila)
        assert "anio" in fila


def test_el_indice_publicado_se_reproduce_con_los_pesos_congelados():
    """El Parquet commiteado tiene que salir de correr `iif index` con los pesos que el contrato fija.

    Sin esto, el índice del repositorio y el que produce el código pueden separarse en silencio, y el atlas
    y la econometría quedarían leyendo un archivo que nadie sabe reproducir.
    """
    import pandas as pd

    if not BASE_DUCKDB.exists():
        pytest.skip(f"sin {BASE_DUCKDB}; corre `make dbt-build`")
    publicado_parquet = config.DATA_PROCESSED / "indice_departamento_anual.parquet"
    if not publicado_parquet.exists():
        pytest.skip("sin índice publicado")

    from iif.index.run import build_level

    _, res = build_level("departamento", congelados=None)
    from iif.index.build import load_contract

    congelados = load_contract().get("pesos_congelados")
    assert congelados, "el contrato tiene que traer los pesos congelados"
    _, con_congelados = build_level("departamento", congelados=congelados)

    esperado = pd.read_parquet(publicado_parquet)[["dpto_ccdgo", "anio", "iif_compuesto"]]
    obtenido = con_congelados.scores[["dpto_ccdgo", "anio", "iif_compuesto"]]
    junto = esperado.merge(obtenido, on=["dpto_ccdgo", "anio"], suffixes=("_pub", "_calc"))
    assert len(junto) == len(esperado)
    diferencia = (junto["iif_compuesto_pub"] - junto["iif_compuesto_calc"]).abs().max()
    assert diferencia < 1e-9, f"el indice publicado no se reproduce; maxima diferencia {diferencia}"

    # Y los pesos del contrato son los que la calibración produce sobre el panel real: si alguien cambia el
    # denominador o la ventana y no recalibra, esto lo dice.
    for dim, fit in res.fits.items():
        for variable, media in fit.media.items():
            assert media == pytest.approx(congelados[dim]["media"][variable], rel=1e-9), (
                f"{dim}/{variable}: el contrato guarda una media que la calibracion actual no produce; "
                "corre `uv run iif index --recalibrar`"
            )

