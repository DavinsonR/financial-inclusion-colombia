"""Cuánto del coeficiente es el denominador: el índice real y el placebo de solo-denominador (ADR-017, ADR-024).

Cinco de las ocho variables del índice son montos sobre el producto, y la dependiente es el crecimiento del
producto. ADR-017 rezagó el denominador y citó en su texto el placebo que lo justificaba (β = −0,2525 con el
producto contemporáneo), pero la cifra no estaba en `resultados.json` (R-09). Aquí se construye y se
publica: el índice real con cada denominador, y un índice placebo con **todos los numeradores congelados en
su valor de 2018**, que por construcción no contiene información financiera y solo se mueve por sus
denominadores. Con el producto fijo el placebo de los montos no se mueve; lo que le queda es la población
en el denominador de los conteos, que también está en la dependiente per cápita.

El índice se construye con `iif.index.build.build_index` y el contrato de `config/index.yaml`, cambiando
solo la clave `denominador`: ninguna regla del índice se duplica aquí (R-15). Cada variante se recalibra,
porque cambiar el denominador cambia la escala de las variables (ADR-015, punto 6).
"""

from __future__ import annotations

import copy

import duckdb
import pandas as pd

from iif import config
from iif.index.build import build_index, contract_variables, load_contract

MODOS = ("contemporaneo", "rezagado", "fijo")
TABLA = "marts.mart_panel_departamento_anual"


def _panel_y_unidades(db: str | None = None) -> tuple[pd.DataFrame, dict[str, str]]:
    ruta = db or str(config.DUCKDB_PATH)
    with duckdb.connect(ruta, read_only=True) as con:
        panel = con.sql(f"select * from {TABLA}").df()
        unidades = dict(con.sql("select variable_id, unidad from seeds.dim_variable").df().values)
    return panel, unidades


def congelar_numeradores(panel: pd.DataFrame, variables: list[str], anio_base: int) -> pd.DataFrame:
    """Cada numerador toma, en todos los años, su valor del año base en la misma unidad."""
    salida = panel.copy()
    base = panel.loc[panel["anio"] == anio_base].set_index("dpto_ccdgo")
    for v in variables:
        salida[v] = salida["dpto_ccdgo"].map(base[v])
    return salida


def indices(db: str | None = None) -> pd.DataFrame:
    """El compuesto real y el placebo con cada denominador, en formato ancho por departamento y año."""
    panel, unidades = _panel_y_unidades(db)
    contrato = load_contract()
    variables = contract_variables(contrato)
    anio_base = int(contrato["calibracion"]["anio_desde"])
    placebo_panel = congelar_numeradores(panel, variables, anio_base)
    salida = panel[["dpto_ccdgo", "anio"]].copy()
    for modo in MODOS:
        c = copy.deepcopy(contrato)
        c["denominador"] = modo
        c.pop("pesos_congelados", None)
        real = build_index(panel, unidades, contract=c).scores
        salida = salida.merge(
            real[["dpto_ccdgo", "anio", "iif_compuesto"]].rename(columns={"iif_compuesto": f"iif_{modo}"}),
            on=["dpto_ccdgo", "anio"],
            how="left",
        )
        try:
            placebo = build_index(placebo_panel, unidades, contract=c).scores
        except ValueError:
            # Con numeradores y producto congelados, los montos no varían en la ventana de calibración y la
            # estandarización no tiene nada que escalar: el placebo no existe, que es la propiedad del fijo.
            salida[f"placebo_{modo}"] = float("nan")
            continue
        salida = salida.merge(
            placebo[["dpto_ccdgo", "anio", "iif_compuesto"]].rename(columns={"iif_compuesto": f"placebo_{modo}"}),
            on=["dpto_ccdgo", "anio"],
            how="left",
        )
    return salida
