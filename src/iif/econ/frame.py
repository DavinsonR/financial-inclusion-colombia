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

# Valor agregado a precios constantes por sección CIIU, para la dependiente sin minería (B) ni actividades
# financieras (K) de ADR-024 (A4). Las filas de sección son las que traen `seccion_ciiu`; los totales
# ("Valor agregado bruto", "PIB DEPARTAMENTAL", impuestos) la traen vacía.
CONSULTA_VA = """
select dpto_ccdgo, anio, seccion_ciiu, va_constante_2015_mm
from staging.stg_dane__va_departamento_actividad_anual
where coalesce(seccion_ciiu, '') <> ''
"""

CONSULTA_VA_TOTAL = """
select dpto_ccdgo, anio, va_constante_2015_mm as va_total
from staging.stg_dane__va_departamento_actividad_anual
where actividad = 'Valor agregado bruto'
"""

# La serie larga del producto, 2005 a 2025. La población solo se une al mart desde 2018, pero el DANE
# publica el PIB per cápita corriente desde 2005: la población implícita (PIB corriente / PIB per cápita
# corriente) coincide con la proyección de población desde 2018 y permite el per cápita real hacia atrás.
CONSULTA_LARGA = """
select
    dpto_ccdgo,
    anio,
    pib_constante_2015_mm,
    pib_corriente_mm * 1e9 / nullif(pib_per_capita_corriente, 0) as poblacion_implicita
from marts.fct_actividad_departamento_anual
order by dpto_ccdgo, anio
"""

# Variantes de la dependiente limpia: qué secciones se quitan del valor agregado.
SIN_SECCIONES = {
    "crecimiento_va_sin_bk": ("B", "K"),
    "crecimiento_va_sin_b": ("B",),
    "crecimiento_va_sin_k": ("K",),
}


def load_frame(db: str | None = None) -> pd.DataFrame:
    """Lee el panel departamental anual y añade las transformaciones de la especificación.

    Las derivadas se calculan aquí y no en dbt porque son decisiones de la estimación, no del almacén:
    el logaritmo del ingreso rezagado (convergencia condicional), el tamaño en logaritmos y el cambio
    del índice, que es la especificación en diferencias.
    """
    ruta = db or str(config.DUCKDB_PATH)
    with duckdb.connect(ruta, read_only=True) as con:
        df = con.sql(CONSULTA).df()
        va = con.sql(CONSULTA_VA).df()

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
        # no construye (B-069). Como la muestra de estimación empieza en 2019 —el crecimiento necesita el
        # nivel anterior— y el índice existe desde 2018, el rezago no cuesta ninguna observación.
        df[f"{col}_rezago"] = df.groupby("dpto_ccdgo", sort=False)[col].shift(1)
    # El adelanto del índice: si el crecimiento de hoy "predice" el índice de mañana, lo que hay es crédito
    # que responde al crecimiento y no al revés (ADR-024, A6). El último año no tiene adelanto.
    df["iif_compuesto_adelanto"] = df.groupby("dpto_ccdgo", sort=False)["iif_compuesto"].shift(-1)
    df["crecimiento_rezago"] = df.groupby("dpto_ccdgo", sort=False)["crecimiento"].shift(1)
    df = df.merge(_crecimiento_sin_secciones(va, df[["dpto_ccdgo", "anio", "poblacion_total"]]),
                  on=["dpto_ccdgo", "anio"], how="left")
    return df.reset_index(drop=True)


def _crecimiento_sin_secciones(va: pd.DataFrame, poblacion: pd.DataFrame) -> pd.DataFrame:
    """Crecimiento del valor agregado constante per cápita sin las secciones que se piden (ADR-024, A4).

    La sección K (actividades financieras) sube con el crédito y las cuentas por construcción, así que está
    mecánicamente a los dos lados de la ecuación; la B (minería) mueve el crecimiento de cinco departamentos
    con precios externos que los efectos de año no absorben de forma homogénea. El volumen encadenado del
    DANE no es aditivo: la suma de secciones se separa del total hasta en unos puntos porcentuales, y esa
    discrepancia se mide y se publica en `run.py`.
    """
    salida = poblacion.copy()
    for columna, fuera in SIN_SECCIONES.items():
        nivel = (
            va[~va["seccion_ciiu"].isin(fuera)]
            .groupby(["dpto_ccdgo", "anio"], as_index=False)["va_constante_2015_mm"]
            .sum()
            .rename(columns={"va_constante_2015_mm": "nivel"})
        )
        junto = poblacion.merge(nivel, on=["dpto_ccdgo", "anio"], how="left").sort_values(["dpto_ccdgo", "anio"])
        pc = np.log(junto["nivel"] / junto["poblacion_total"].where(lambda s: s > 0))
        junto[columna] = pc.groupby(junto["dpto_ccdgo"], sort=False).diff()
        salida = salida.merge(junto[["dpto_ccdgo", "anio", columna]], on=["dpto_ccdgo", "anio"], how="left")
    return salida.drop(columns=["poblacion_total"])


def load_serie_larga(db: str | None = None) -> pd.DataFrame:
    """El producto real 2005–2025 por departamento, total y per cápita, con su crecimiento.

    Es la dependiente del contraste de tendencias previas (ADR-024, A2) y de la sigma-convergencia: la
    exposición se fija en 2018, pero lo que se contrasta es si los más expuestos ya crecían distinto antes,
    y eso solo lo dice una serie que empiece antes que el índice.
    """
    ruta = db or str(config.DUCKDB_PATH)
    with duckdb.connect(ruta, read_only=True) as con:
        df = con.sql(CONSULTA_LARGA).df()
    df["anio"] = df["anio"].astype(int)
    df = df.sort_values(["dpto_ccdgo", "anio"]).reset_index(drop=True)
    df["log_pib_real"] = np.log(df["pib_constante_2015_mm"].where(lambda s: s > 0))
    df["log_pib_real_pc"] = np.log(
        (df["pib_constante_2015_mm"] * 1e9 / df["poblacion_implicita"]).where(lambda s: s > 0)
    )
    por = df.groupby("dpto_ccdgo", sort=False)
    df["crecimiento_pib_total"] = por["log_pib_real"].diff()
    df["crecimiento_pib_pc"] = por["log_pib_real_pc"].diff()
    return df


def discrepancia_va(db: str | None = None) -> dict:
    """Cuánto se separa la suma de secciones del valor agregado total a precios constantes (no aditividad)."""
    ruta = db or str(config.DUCKDB_PATH)
    with duckdb.connect(ruta, read_only=True) as con:
        va = con.sql(CONSULTA_VA).df()
        total = con.sql(CONSULTA_VA_TOTAL).df()
    suma = va.groupby(["dpto_ccdgo", "anio"], as_index=False)["va_constante_2015_mm"].sum()
    junto = suma.merge(total, on=["dpto_ccdgo", "anio"])
    junto = junto[junto["anio"] >= 2018]
    rel = junto["va_constante_2015_mm"] / junto["va_total"] - 1
    return {
        "desde": 2018,
        "max_abs": float(rel.abs().max()),
        "mediana_abs": float(rel.abs().median()),
    }


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
