"""El marco de estimación: una fila por departamento y año, con lo que las regresiones necesitan.

El grano es anual porque el producto subnacional es anual (ADR-001). La dependiente es la tasa de
crecimiento del PIB real per cápita, ya construida en el mart, y el regresor de interés es el índice de
inclusión financiera con sus tres dimensiones (ADR-015).
"""

from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

from iif import config

CONSULTA = """
select
    i.dpto_ccdgo,
    i.departamento,
    i.region,
    i.anio,
    i.iif_compuesto,
    i.iif_acceso,
    i.iif_uso,
    i.iif_profundidad,
    i.iif_sensibilidad_pca,
    i.iif_sensibilidad_sarma,
    p.crecimiento_pib_real_pc          as crecimiento,
    p.pib_real_per_capita,
    p.pib_real_per_capita_rezago,
    p.tasa_urbanizacion,
    p.poblacion_total,
    p.cobertura_neta_ponderada,
    p.accesos_internet_q4
from marts.mart_indice_departamento_anual as i
join marts.mart_panel_departamento_anual as p
    on p.dpto_ccdgo = i.dpto_ccdgo and p.anio = i.anio
order by i.dpto_ccdgo, i.anio
"""


def load_frame(db: str | None = None) -> pd.DataFrame:
    """Lee el panel departamental anual y añade las transformaciones de la especificación.

    Las derivadas se calculan aquí y no en dbt porque son decisiones de la estimación, no del almacén:
    el logaritmo del ingreso rezagado (convergencia condicional), el tamaño en logaritmos y el cambio
    del índice, que es la especificación en diferencias.
    """
    ruta = db or str(config.DUCKDB_PATH)
    with duckdb.connect(ruta, read_only=True) as con:
        df = con.sql(CONSULTA).df()

    df["anio"] = df["anio"].astype(int)
    df["log_pib_rezago"] = np.log(df["pib_real_per_capita_rezago"].where(lambda s: s > 0))
    # El nivel contemporaneo en logaritmos existe desde 2018, que el rezago no: es la exposicion inicial
    # de ingreso para los contrastes del shift-share.
    df["log_pib"] = np.log(df["pib_real_per_capita"].where(lambda s: s > 0))
    df["log_poblacion"] = np.log(df["poblacion_total"].where(lambda s: s > 0))
    df["log_internet"] = np.log1p(df["accesos_internet_q4"])
    df = df.sort_values(["dpto_ccdgo", "anio"])
    for col in ("iif_compuesto", "iif_acceso", "iif_uso", "iif_profundidad"):
        df[f"d_{col}"] = df.groupby("dpto_ccdgo", sort=False)[col].diff()
        # El rezago del índice: ordena la relación en el tiempo sin pretender identificarla. Existe como
        # columna para que la especificación pueda elegirlo y para que el texto no prometa lo que el código
        # no construye (B-049). Como la muestra de estimación empieza en 2019 —el crecimiento necesita el
        # nivel anterior— y el índice existe desde 2018, el rezago no cuesta ninguna observación.
        df[f"{col}_rezago"] = df.groupby("dpto_ccdgo", sort=False)[col].shift(1)
    return df.reset_index(drop=True)


def estimation_sample(df: pd.DataFrame, y: str, x: str, controls: list[str]) -> pd.DataFrame:
    """Las filas completas de una especificación, para que N sea el mismo en cada tabla.

    Se recorta una sola vez y explícitamente: una N que cambia entre columnas de la misma tabla no se
    puede comparar, y es la forma más silenciosa de que dos coeficientes parezcan distintos.
    """
    columnas = ["dpto_ccdgo", "departamento", "region", "anio", y, x, *controls]
    return df.loc[:, columnas].dropna().reset_index(drop=True)


def as_panel(df: pd.DataFrame) -> pd.DataFrame:
    """Índice de dos niveles (unidad, tiempo) que es lo que espera linearmodels."""
    return df.set_index(["dpto_ccdgo", "anio"], drop=False)
