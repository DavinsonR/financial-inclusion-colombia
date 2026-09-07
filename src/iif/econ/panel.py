"""Estimaciones de panel y la aritmética de sus errores estándar.

Todas las especificaciones llevan efectos fijos de entidad **y de tiempo**. Los de entidad quitan lo que
distingue de forma permanente a un departamento; los de tiempo quitan lo que le pasa al país entero en un
año. Sin los segundos, cualquier variable que suba con los años se correlaciona con cualquier otra que
también suba, y el coeficiente mide la coincidencia de dos tendencias nacionales.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS

from iif.econ.frame import as_panel


@dataclass
class Estimacion:
    """Un coeficiente con todo lo que hace falta para juzgarlo."""

    nombre: str
    variable: str
    coef: float
    se: float
    t: float
    p: float
    ic_bajo: float
    ic_alto: float
    n: int
    unidades: int
    periodos: int
    r2_within: float
    errores: str
    controles: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        d = self.__dict__.copy()
        d["controles"] = list(self.controles)
        return d


def _resumen(res, variable: str, nombre: str, errores: str, controles: list[str]) -> Estimacion:
    return Estimacion(
        nombre=nombre,
        variable=variable,
        coef=float(res.params[variable]),
        se=float(res.std_errors[variable]),
        t=float(res.tstats[variable]),
        p=float(res.pvalues[variable]),
        ic_bajo=float(res.conf_int().loc[variable, "lower"]),
        ic_alto=float(res.conf_int().loc[variable, "upper"]),
        n=int(res.nobs),
        unidades=int(res.entity_info["total"]),
        periodos=int(res.time_info["total"]),
        r2_within=float(res.rsquared_within),
        errores=errores,
        controles=list(controles),
    )


def two_way_fe(
    df: pd.DataFrame,
    y: str,
    x: str,
    controls: list[str] | None = None,
    *,
    errores: str = "cluster",
    nombre: str = "two-way FE",
    time_effects: bool = True,
):
    """Efectos fijos de entidad y tiempo, con la familia de errores que se pida.

    `cluster` agrupa por departamento, que es donde vive la correlación serial; `driscoll-kraay` además
    admite dependencia entre departamentos en el mismo año, que es exactamente lo que la prueba CD busca.
    Con 33 clústeres la aproximación asintótica del clúster ya empieza a quedarse corta: por eso el
    resultado principal se acompaña siempre de un bootstrap salvaje (`robustness.wild_cluster_bootstrap`).
    """
    controls = list(controls or [])
    panel = as_panel(df)
    exog = panel[[x, *controls]].assign(const=1.0)
    modelo = PanelOLS(panel[y], exog, entity_effects=True, time_effects=time_effects)
    if errores == "cluster":
        res = modelo.fit(cov_type="clustered", cluster_entity=True)
    elif errores == "driscoll-kraay":
        res = modelo.fit(cov_type="kernel", kernel="bartlett")
    elif errores == "robusto":
        res = modelo.fit(cov_type="robust")
    else:
        raise ValueError(f"familia de errores desconocida: {errores}")
    return _resumen(res, x, nombre, errores, controls), res


def pooled_entity_only(df: pd.DataFrame, y: str, x: str, controls: list[str] | None = None):
    """La misma ecuación sin efectos de tiempo.

    No es una alternativa que se proponga: es el contraste que enseña cuánto del coeficiente era tendencia
    común. Se publica al lado del principal precisamente para que la diferencia se vea.
    """
    return two_way_fe(df, y, x, controls, nombre="solo efectos de entidad", time_effects=False)


def in_changes(df: pd.DataFrame, y: str, x: str, controls: list[str] | None = None):
    """La especificación en cambios del índice.

    Si el nivel del índice y el crecimiento comparten una raíz común, la relación en niveles puede ser
    espuria aunque los efectos fijos estén puestos. En cambios esa raíz desaparece, a cambio de amplificar
    el ruido de medida.
    """
    return two_way_fe(df, y, f"d_{x}", controls, nombre="en cambios del índice")


def by_dimension(df: pd.DataFrame, y: str, controls: list[str] | None = None) -> list[Estimacion]:
    """Acceso, uso y profundidad por separado, cada una en su propia regresión.

    Meterlas juntas en una sola ecuación mide el efecto parcial de cada dimensión manteniendo las otras
    fijas, que no es la pregunta: las tres se mueven juntas por construcción del índice.
    """
    salida = []
    for dim in ("iif_acceso", "iif_uso", "iif_profundidad"):
        sub = df.dropna(subset=[y, dim, *(controls or [])])
        est, _ = two_way_fe(sub, y, dim, controls, nombre=f"dimensión: {dim.removeprefix('iif_')}")
        salida.append(est)
    return salida


def residuals_wide(res) -> pd.DataFrame:
    """Residuos como matriz unidad × tiempo, que es lo que consumen CD y Moran."""
    r = res.resids.copy()
    r.index = res.resids.index
    ancho = r.unstack(level=0)
    ancho.index = np.asarray(ancho.index)
    return ancho
