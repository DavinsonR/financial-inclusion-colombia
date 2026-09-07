"""Diseños que no dependen de que el índice sea exógeno: CCE, shift-share, eventos y espacial.

Los efectos fijos de dos vías quitan lo permanente de cada departamento y lo común de cada año, pero no un
choque que golpee distinto a departamentos distintos. Estos cuatro diseños atacan ese hueco por caminos
independientes, y su valor está en que fallen o sobrevivan **juntos**.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from iif.econ.diagnostics import matriz_pesos
from iif.econ.panel import Estimacion, two_way_fe


def cce_pooled(df: pd.DataFrame, y: str, x: str, controls: list[str] | None = None):
    """Efectos correlacionados comunes de Pesaran (2006), versión agrupada con cargas heterogéneas.

    Se añaden las medias transversales por año de la dependiente y del regresor, **interactuadas con cada
    departamento**. Bajo el modelo de factores esas medias son un sustituto observable de los factores
    comunes no observados —la trayectoria nacional, el petróleo, la pandemia— y dejar que cada unidad les
    cargue distinto es lo que distingue este diseño de un simple efecto de tiempo: un choque nacional que
    golpea el doble a un departamento que a otro deja de confundirse con el índice.

    No lleva efectos de tiempo: con ellos, las medias serían idénticas a los dummies de año y el modelo
    no se puede estimar. Sí lleva efectos de entidad. Cuesta 2·N parámetros, que con 33 departamentos y
    231 observaciones deja 129 grados de libertad: suficiente, pero conviene saberlo.
    """
    controls = list(controls or [])
    datos = df.dropna(subset=[y, x, *controls]).copy()
    for col in (y, x):
        datos[f"cs_{col}"] = datos.groupby("anio", sort=False)[col].transform("mean")
    cargas = []
    for unidad in sorted(datos["dpto_ccdgo"].unique()):
        es = (datos["dpto_ccdgo"] == unidad).astype(float)
        for col in (y, x):
            nombre = f"cs_{col}_{unidad}"
            datos[nombre] = datos[f"cs_{col}"] * es
            cargas.append(nombre)
    est, res = two_way_fe(
        datos, y, x, [*controls, *cargas], nombre="CCE (cargas heterogéneas)", time_effects=False
    )
    est.controles = [*controls, "medias transversales × departamento"]
    return est, res


def exposicion_inicial(marco: pd.DataFrame, x: str, anio_base: int) -> pd.Series:
    """El nivel del índice de cada departamento en el año base, indexado por departamento.

    Se mide en el marco completo y no en la muestra de estimación: el crecimiento de 2018 no existe
    (necesita el nivel de 2017), pero el índice de 2018 sí, y esa es justo la exposición **anterior** a
    cualquier observación de la dependiente. Medirla dentro de la muestra la haría contemporánea del
    crecimiento del primer año, que es lo que un diseño de exposición existe para evitar.
    """
    base = marco.loc[marco["anio"] == anio_base, ["dpto_ccdgo", x]].dropna()
    unidades = marco["dpto_ccdgo"].nunique()
    if len(base) < 0.9 * unidades:
        # Una variable que no existe en el año base (un rezago, por ejemplo) llega aqui como columna
        # vacia y mas adelante rompe el estimador con un error de rango que no dice de donde viene.
        raise ValueError(f"{x} solo tiene {len(base)} de {unidades} departamentos en {anio_base}")
    return base.set_index("dpto_ccdgo")[x].rename("exposicion")


def shift_share(
    df: pd.DataFrame,
    y: str,
    x: str,
    exposicion: pd.Series,
    controls: list[str] | None = None,
    *,
    nacional: pd.Series | None = None,
) -> tuple[Estimacion, pd.DataFrame]:
    """Exposición inicial × adopción nacional.

    El regresor deja de ser el índice observado y pasa a ser el que le habría tocado a cada departamento si
    solo hubiera seguido la adopción nacional desde su posición inicial. Así la variación viene de una
    condición previa al periodo y de una trayectoria agregada, y no de lo que ese departamento hizo en el
    mismo año en que creció. Con efectos de tiempo, lo que identifica es la **pendiente diferencial** de
    los departamentos más expuestos al principio.
    """
    controls = list(controls or [])
    datos = df.dropna(subset=[y, x, *controls]).copy()
    serie_nacional = nacional if nacional is not None else datos.groupby("anio")[x].mean()
    datos["adopcion_nacional"] = datos["anio"].map(serie_nacional)
    datos["shift_share"] = datos["dpto_ccdgo"].map(exposicion) * datos["adopcion_nacional"]
    datos = datos.dropna(subset=["shift_share"])
    est, _ = two_way_fe(datos, y, "shift_share", controls, nombre="shift-share (exposición 2018 × adopción)")
    return est, datos


def event_study(
    df: pd.DataFrame,
    y: str,
    x: str,
    exposicion: pd.Series,
    *,
    anio_evento: int = 2020,
    referencia: int = -1,
) -> pd.DataFrame:
    """Estudio de eventos alrededor de 2020, con la exposición previa como intensidad del tratamiento.

    2020 es el año en que la transferencia monetaria de emergencia abrió cuentas a millones de hogares. Si
    la inclusión financiera empuja el crecimiento, los departamentos más expuestos antes del choque
    deberían separarse **después** y no antes. Con la dependiente empezando en 2019, solo hay un año
    anterior al choque y es el de referencia: este diseño no puede contrastar tendencias previas, y se
    publica diciéndolo. Lo que sí mide es en qué años posteriores se separan los más expuestos.
    """
    datos = df.dropna(subset=[y, x]).copy()
    exposicion = (exposicion - exposicion.mean()) / exposicion.std(ddof=1)
    datos["exposicion"] = datos["dpto_ccdgo"].map(exposicion)
    datos = datos.dropna(subset=["exposicion"])
    datos["k"] = datos["anio"] - anio_evento

    filas = []
    for k in sorted(datos["k"].unique()):
        if k == referencia:
            filas.append(
                {"k": int(k), "anio": anio_evento + int(k), "coef": 0.0, "se": 0.0, "referencia": True}
            )
            continue
        datos[f"ev_{k}"] = datos["exposicion"] * (datos["k"] == k).astype(float)
    interacciones = [c for c in datos.columns if c.startswith("ev_")]
    if not interacciones:
        return pd.DataFrame(filas)
    est, res = two_way_fe(datos, y, interacciones[0], interacciones[1:], nombre="estudio de eventos")
    for col in interacciones:
        k = int(col.removeprefix("ev_"))
        filas.append(
            {
                "k": k,
                "anio": anio_evento + k,
                "coef": float(res.params[col]),
                "se": float(res.std_errors[col]),
                "referencia": False,
            }
        )
    salida = pd.DataFrame(filas).sort_values("k").reset_index(drop=True)
    salida["ic_bajo"] = salida["coef"] - 1.96 * salida["se"]
    salida["ic_alto"] = salida["coef"] + 1.96 * salida["se"]
    return salida


def slx(df: pd.DataFrame, y: str, x: str, vecinos: dict[str, list[str]], controls: list[str] | None = None):
    """Modelo con el rezago espacial del regresor (SLX).

    Se añade la media del índice de los departamentos vecinos. Si el coeficiente propio se sostiene con el
    del vecino dentro, la relación no era el reflejo de un vecindario; si se desploma, lo era. Se prefiere
    el rezago del regresor y no el de la dependiente porque el segundo exige estimación por máxima
    verosimilitud y supuestos que un panel de ocho años no puede sostener.
    """
    controls = list(controls or [])
    datos = df.dropna(subset=[y, x, *controls]).copy()
    unidades = sorted(datos["dpto_ccdgo"].unique())
    W = matriz_pesos(unidades, vecinos)
    idx = {u: i for i, u in enumerate(unidades)}
    piezas = []
    for _anio, sub in datos.groupby("anio", sort=True):
        v = np.full(len(unidades), np.nan)
        for u, valor in zip(sub["dpto_ccdgo"], sub[x], strict=True):
            v[idx[u]] = valor
        disponible = np.isfinite(v)
        Wa = W[:, disponible]
        filas = Wa.sum(axis=1, keepdims=True)
        with np.errstate(invalid="ignore", divide="ignore"):
            Wa = np.where(filas > 0, Wa / filas, 0.0)
        rezago = Wa @ v[disponible]
        rezago[filas.ravel() == 0] = np.nan
        pieza = sub.copy()
        pieza[f"w_{x}"] = [rezago[idx[u]] for u in sub["dpto_ccdgo"]]
        piezas.append(pieza)
    datos = pd.concat(piezas).dropna(subset=[f"w_{x}"])
    return two_way_fe(datos, y, x, [*controls, f"w_{x}"], nombre="SLX (rezago espacial del índice)")
