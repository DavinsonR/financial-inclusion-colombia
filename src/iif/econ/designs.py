"""Diseños complementarios: CCE, exposición inicial, estudio de eventos, tendencias previas y espacial.

Los efectos fijos de dos vías quitan lo permanente de cada departamento y lo común de cada año, pero no un
choque que golpee distinto a departamentos distintos. Estos diseños atacan ese hueco por caminos distintos.
Ninguno identifica un efecto causal por sí solo: el de exposición inicial exige que el nivel de 2018 sea
exógeno, y su placebo de urbanización muestra que no lo es (ADR-024). Su valor está en que fallen o
sobrevivan **juntos**.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from iif.econ import inference
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


def exposicion_por_adopcion(
    df: pd.DataFrame,
    y: str,
    x: str,
    exposicion: pd.Series,
    controls: list[str] | None = None,
    *,
    nacional: pd.Series | None = None,
) -> tuple[Estimacion, pd.DataFrame]:
    """Diseño de exposición inicial: nivel de 2018 × adopción nacional.

    Se llamaba "shift-share" y no lo es en el sentido de Goldsmith-Pinkham, Sorkin y Swift o de Borusyak,
    Hull y Jaravel: hay una sola participación y una sola serie común, sin muchos choques ni pesos de
    Rotemberg (ADR-024, O5). La columna del regresor conserva el nombre `shift_share` porque la leen el
    bootstrap y el placebo de `run.py`.

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
    est, _ = two_way_fe(
        datos, y, "shift_share", controls, nombre="exposición inicial (índice 2018 × adopción nacional)"
    )
    return est, datos


# El nombre viejo se conserva como alias: lo usan las pruebas y cualquier cuaderno que lo importe.
shift_share = exposicion_por_adopcion


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
    deberían separarse **después** y no antes. Con la dependiente per cápita empezando en 2019, aquí solo
    hay un año anterior al choque y es el de referencia; las tendencias previas se contrastan aparte, con la
    serie larga del producto (`tendencias_previas`, ADR-024).
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


def tendencias_previas(
    larga: pd.DataFrame,
    y: str,
    exposicion: pd.Series,
    *,
    anio_referencia: int = 2019,
    anio_evento: int = 2020,
    controles_iniciales: dict[str, pd.Series] | None = None,
    replicas: int = 999,
    semilla: int = 20260907,
) -> dict:
    """Estudio de eventos sobre la serie larga, con la prueba conjunta de los coeficientes previos.

    La exposición es fija (el índice de 2018 estandarizado), así que no hace falta el índice en los años
    anteriores: lo que se pregunta es si los departamentos más expuestos ya crecían distinto antes del
    choque. Se estima exposición × año para todos los años salvo el de referencia, con efectos de entidad y
    de año, y se contrasta que los coeficientes anteriores a `anio_referencia` sean cero a la vez: F contra
    F(q, G − 1) con el error agrupado y, al lado, el bootstrap salvaje del Wald con la nula impuesta.

    `controles_iniciales` añade cada condición inicial × año (por ejemplo, la urbanización de 2018): si la
    pendiente de los expuestos es la de los urbanos, desaparece con ella dentro.
    """
    z = (exposicion - exposicion.mean()) / exposicion.std(ddof=1)
    datos = larga[["dpto_ccdgo", "anio", y]].copy()
    datos["exposicion"] = datos["dpto_ccdgo"].map(z)
    datos = datos.dropna(subset=[y, "exposicion"]).reset_index(drop=True)
    anios = sorted(int(a) for a in datos["anio"].unique())
    eventos = []
    for a in anios:
        if a == anio_referencia:
            continue
        col = f"ev_{a}"
        datos[col] = datos["exposicion"] * (datos["anio"] == a).astype(float)
        eventos.append(col)
    controles = []
    for nombre, serie in (controles_iniciales or {}).items():
        datos[f"_{nombre}"] = datos["dpto_ccdgo"].map(serie)
        for a in anios[1:]:
            col = f"{nombre}_x_{a}"
            datos[col] = datos[f"_{nombre}"] * (datos["anio"] == a).astype(float)
            controles.append(col)
    datos = datos.dropna(subset=[*eventos, *controles]).reset_index(drop=True)

    d = inference.diseno(datos, y, [*eventos, *controles])
    todos = inference.crve(d, list(range(len(eventos))))
    previos = [i for i, c in enumerate(eventos) if int(c.removeprefix("ev_")) < anio_referencia]
    posteriores = [i for i, c in enumerate(eventos) if int(c.removeprefix("ev_")) >= anio_evento]
    gl = d.G - 1

    coeficientes = []
    for i, col in enumerate(eventos):
        b, se = float(todos["coef"][i]), float(todos["se"][i])
        coeficientes.append(
            {
                "anio": int(col.removeprefix("ev_")),
                "coef": b,
                "se": se,
                "p": float(2 * stats.t.sf(abs(b / se), gl)) if se > 0 else float("nan"),
                "referencia": False,
            }
        )
    coeficientes.append({"anio": anio_referencia, "coef": 0.0, "se": 0.0, "p": None, "referencia": True})
    coeficientes.sort(key=lambda f: f["anio"])
    return {
        "dependiente": y,
        "anios": [anios[0], anios[-1]],
        "anio_referencia": anio_referencia,
        "controles_iniciales": sorted(controles_iniciales or {}),
        "n": d.n,
        "clusteres": d.G,
        "previos": wald_resumen(d, previos, replicas=replicas, semilla=semilla),
        "posteriores": wald_resumen(d, posteriores, replicas=replicas, semilla=semilla),
        "coeficientes": coeficientes,
    }


def wald_resumen(d: inference.Diseno, idx: list[int], *, replicas: int, semilla: int) -> dict:
    """La prueba conjunta con el F agrupado y los dos bootstraps (Rademacher y Webb)."""
    rad = inference.wald_bootstrap(d, idx, replicas=replicas, semilla=semilla, pesos="rademacher")
    webb = inference.wald_bootstrap(d, idx, replicas=replicas, semilla=semilla, pesos="webb")
    return {
        "q": rad["q"],
        "F": rad["F"],
        "gl": rad["gl"],
        "p_F": rad["p_F"],
        "p_bootstrap": rad["p_bootstrap"],
        "p_bootstrap_webb": webb["p_bootstrap"],
        "replicas": rad["replicas"],
    }
