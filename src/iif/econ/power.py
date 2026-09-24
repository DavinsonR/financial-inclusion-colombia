"""Lo que a un nulo le falta para decir algo: qué efecto podría esconder y cuáles descarta.

Un contraste que no rechaza la nula no distingue entre "el efecto es cero" y "este diseño no lo vería
aunque existiera". La cifra que separa las dos lecturas es el efecto mínimo detectable, y depende del error
estándar, no del coeficiente: por eso se puede calcular y por eso es informativo, al contrario que la
llamada potencia retrospectiva, que es una transformación monótona del p-valor y no aporta nada (ADR-018).

La segunda pieza es la prueba de equivalencia. El p-valor responde "¿puedo descartar que el efecto sea
exactamente cero?", que casi nunca es la pregunta. El TOST responde "¿puedo descartar que el efecto sea
mayor que este tamaño?", que es la que un lector hace de verdad.

Con errores agrupados por departamento, la distribución de referencia es t(G − 1), no la de los grados de
libertad residuales (ADR-024): con 33 clústeres hay 32 grados de libertad, no 186.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from iif.econ.robustness import demean_two_way

# Márgenes de equivalencia por defecto, en puntos porcentuales de crecimiento anual por desviación típica
# identificante del regresor. Se publican tres porque el repositorio todavía no tiene una bibliografía que
# fije un tamaño de efecto previo defendible (ADR-018); el lector escoge el suyo.
MARGENES_PP = (0.25, 0.50, 1.00)


def mde(se: float, *, potencia: float = 0.80, alfa: float = 0.05, gl: int | None = None) -> float:
    """Efecto mínimo detectable: el coeficiente más pequeño que este diseño rechazaría con esa potencia.

    Es la suma de dos valores críticos por el error estándar: uno para no confundir ruido con señal
    (`alfa`, dos colas) y otro para que la señal caiga del lado correcto con la frecuencia que se pide
    (`potencia`, una cola). Con la normal, alfa de 0,05 y potencia de 0,80 el factor es 2,802; con t(32),
    que es la referencia con 33 clústeres (ADR-024), sube a 2,891.
    """
    if not np.isfinite(se) or se <= 0:
        return float("nan")
    if gl is None:
        factor = stats.norm.ppf(1 - alfa / 2) + stats.norm.ppf(potencia)
    else:
        factor = stats.t.ppf(1 - alfa / 2, gl) + stats.t.ppf(potencia, gl)
    return float(factor * se)


def tost(coef: float, se: float, margen: float, gl: int) -> dict:
    """Dos contrastes unilaterales: ¿el efecto está dentro de ±`margen`? (Schuirmann, 1987).

    La nula del TOST es la contraria a la habitual: supone que el efecto **sí** es grande, y se rechaza
    cuando los datos lo empujan dentro del margen por los dos lados a la vez. El p-valor es el mayor de los
    dos unilaterales, que es lo que hace que rechazar signifique equivalencia y no casualidad en un lado.
    """
    if not np.isfinite(se) or se <= 0 or gl <= 0:
        return {"margen": float(margen), "p": float("nan"), "equivale": None}
    p_inferior = float(stats.t.sf((coef + margen) / se, gl))
    p_superior = float(stats.t.cdf((coef - margen) / se, gl))
    p = max(p_inferior, p_superior)
    return {"margen": float(margen), "p": p, "equivale": bool(p < 0.05)}


def residuo_identificante(
    datos: pd.DataFrame,
    x: str,
    controles: list[str] | None = None,
    *,
    unidad: str = "dpto_ccdgo",
    tiempo: str = "anio",
    efectos_tiempo: bool = True,
) -> np.ndarray:
    """x̃: el regresor tras quitar los efectos fijos y residualizar contra los controles (FWL).

    Es la variación con la que se estima el coeficiente, fila por fila. Su cuadrado sumado por unidad da
    los pesos de Aronow y Samii (2016). Sin efectos de tiempo se quitan solo las medias de unidad, que es la
    escala de la especificación "solo entidad" (ADR-024, A10).
    """
    controles = list(controles or [])
    cols = [x, *controles]
    if efectos_tiempo:
        Z = demean_two_way(datos, cols, unidad, tiempo)
    else:
        Z = (datos[cols] - datos.groupby(unidad)[cols].transform("mean")).to_numpy(dtype=float)
    if not controles:
        return Z[:, 0]
    objetivo, regresores = Z[:, 0], Z[:, 1:]
    beta, *_ = np.linalg.lstsq(regresores, objetivo, rcond=None)
    return objetivo - regresores @ beta


def escala_del_regresor(
    df: pd.DataFrame,
    x: str,
    controles: list[str] | None = None,
    *,
    unidad: str = "dpto_ccdgo",
    tiempo: str = "anio",
    efectos_tiempo: bool = True,
) -> dict:
    """Cuánta variación del regresor sobrevive a los efectos fijos, que es la que identifica el coeficiente.

    Un coeficiente se interpreta por desviación típica del regresor, y en un panel con efectos fijos hay
    dos desviaciones muy distintas: la del regresor tal como se mide y la que queda después de quitar lo
    que es permanente de cada unidad y común de cada año. Publicar el MDE en la primera exagera el diseño;
    publicarlo solo en la segunda esconde cuánta variación se tiró. Van las dos.

    Con `efectos_tiempo=False` la identificante es la que queda tras los efectos de unidad y los controles:
    es la escala correcta de la especificación "solo entidad", que la curva escalaba con la de dos vías.
    """
    controles = list(controles or [])
    datos = df.dropna(subset=[x, *controles, unidad, tiempo]).reset_index(drop=True)
    bruta = float(datos[x].std(ddof=1))

    solo_unidad = datos[x] - datos.groupby(unidad)[x].transform("mean")
    dos_vias = demean_two_way(datos, [x], unidad, tiempo)[:, 0]
    identificante = residuo_identificante(
        datos, x, controles, unidad=unidad, tiempo=tiempo, efectos_tiempo=efectos_tiempo
    )

    sd_ident = float(np.std(identificante, ddof=1))
    return {
        "de_bruta": bruta,
        "de_sin_efectos_de_entidad": float(solo_unidad.std(ddof=1)),
        "de_sin_efectos_de_dos_vias": float(np.std(dos_vias, ddof=1)),
        "de_identificante": sd_ident,
        # La fracción de varianza que sobrevive, que es el número que explica por qué el MDE es el que es.
        "varianza_que_identifica": float((sd_ident / bruta) ** 2) if bruta > 0 else float("nan"),
        "n": int(len(datos)),
    }


def pesos_aronow_samii(
    df: pd.DataFrame,
    x: str,
    controles: list[str] | None = None,
    *,
    unidad: str = "dpto_ccdgo",
    tiempo: str = "anio",
) -> pd.Series:
    """Qué parte del coeficiente aporta cada unidad: su participación en Σ x̃² (Aronow y Samii, 2016).

    Con efectos fijos, MCO pondera cada unidad por la varianza que le queda al regresor dentro de ella. Un
    coeficiente estimado sobre 33 departamentos puede estar hecho, en la práctica, de unos pocos.
    """
    controles = list(controles or [])
    datos = df.dropna(subset=[x, *controles, unidad, tiempo]).reset_index(drop=True)
    xt = residuo_identificante(datos, x, controles, unidad=unidad, tiempo=tiempo)
    cuadrado = pd.Series(xt**2, index=datos[unidad].to_numpy())
    por_unidad = cuadrado.groupby(level=0).sum()
    return (por_unidad / por_unidad.sum()).rename("peso_aronow_samii")


def grados_de_libertad(n: int, unidades: int, periodos: int, regresores: int) -> int:
    """Los que quedan tras absorber un intercepto por unidad y otro por periodo, menos uno por colinealidad.

    Con errores agrupados ya no son la referencia de ningún contraste (ADR-024): se publican al lado para
    que se vea de dónde salía el 186.
    """
    return int(n - (unidades + periodos - 1) - regresores)


def resumen(
    estimacion,
    df: pd.DataFrame,
    x: str,
    controles: list[str] | None = None,
    *,
    margenes_pp: tuple[float, ...] = MARGENES_PP,
    unidad: str = "dpto_ccdgo",
    tiempo: str = "anio",
    bootstrap: dict | None = None,
) -> dict:
    """El bloque de potencia que `resultados.json` publica al lado del coeficiente (ADR-018, ADR-024).

    Todo se calcula sobre la estimación que se le pasa: si la especificación cambia, el error estándar
    cambia y el MDE cambia con él. Ninguna de estas cifras se escribe a mano en ningún sitio.

    La referencia del TOST, del MDE y del intervalo analítico es t(G − 1). Si se pasa `bootstrap` —el bloque
    de `robustness.wild_cluster_bootstrap` con `invertir` y `margenes`—, el intervalo por inversión y el TOST
    bootstrap se traducen a la misma escala y se publican al lado.
    """
    controles = list(controles or [])
    escala = escala_del_regresor(df, x, controles, unidad=unidad, tiempo=tiempo)
    sd, bruta = escala["de_identificante"], escala["de_bruta"]
    gl = int(estimacion.unidades - 1)
    gl_residual = grados_de_libertad(estimacion.n, estimacion.unidades, estimacion.periodos, 1 + len(controles))

    def a_pp(valor: float) -> float:
        """De unidades del índice a puntos porcentuales de crecimiento por desviación identificante."""
        return float(valor * sd * 100)

    def a_pp_bruta(valor: float) -> float:
        return float(valor * bruta * 100)

    mde80, mde50 = mde(estimacion.se, potencia=0.80, gl=gl), mde(estimacion.se, potencia=0.50, gl=gl)
    critico = float(stats.t.ppf(0.975, gl))
    ic = [estimacion.coef - critico * estimacion.se, estimacion.coef + critico * estimacion.se]
    # El margen más pequeño que el TOST analítico declara equivalente: el extremo más lejano del IC al 90 %.
    critico_90 = float(stats.t.ppf(0.95, gl))
    margen_minimo = max(abs(estimacion.coef - critico_90 * estimacion.se),
                        abs(estimacion.coef + critico_90 * estimacion.se))
    salida = {
        "escala_del_regresor": escala,
        "grados_de_libertad": gl,
        "referencia": "t(G - 1), G = departamentos (clusteres)",
        "grados_de_libertad_residuales": gl_residual,
        "mde": {
            "potencia_80": mde80,
            "potencia_80_pp_por_de": a_pp(mde80),
            "potencia_50": mde50,
            "potencia_50_pp_por_de": a_pp(mde50),
            "potencia_80_pp_por_de_bruta": a_pp_bruta(mde80),
        },
        "intervalo": {
            "ic95": ic,
            "ic95_pp_por_de": [a_pp(v) for v in ic],
            "ic95_pp_por_de_bruta": [a_pp_bruta(v) for v in ic],
        },
        # El margen se pide en puntos porcentuales, que es la unidad en la que se piensa el efecto, y se
        # traduce a unidades del índice para contrastarlo contra el coeficiente.
        "equivalencia": [
            {
                **tost(estimacion.coef, estimacion.se, (pp / 100) / sd, gl),
                "margen_pp_por_de": float(pp),
                "margen_pp_por_de_bruta": float(pp * bruta / sd),
            }
            for pp in margenes_pp
            if sd > 0
        ],
        "margen_minimo": {
            "unidades": margen_minimo,
            "pp_por_de": a_pp(margen_minimo),
            "pp_por_de_bruta": a_pp_bruta(margen_minimo),
        },
    }
    if bootstrap:
        ic95 = bootstrap.get("ic95_bootstrap") or []
        ic90 = bootstrap.get("ic90_bootstrap") or []
        salida["bootstrap"] = {
            "pesos": bootstrap.get("pesos"),
            "p": bootstrap.get("p_bootstrap"),
            "ic95": ic95,
            "ic95_pp_por_de": [a_pp(v) for v in ic95],
            "ic95_pp_por_de_bruta": [a_pp_bruta(v) for v in ic95],
            "ic90": ic90,
            "ic90_pp_por_de": [a_pp(v) for v in ic90],
            "equivalencia": [
                {**t, "margen_pp_por_de": float(t["margen"] * sd * 100)}
                for t in bootstrap.get("tost_bootstrap", [])
            ],
        }
        minimo = bootstrap.get("margen_minimo_bootstrap")
        if minimo is not None:
            salida["bootstrap"]["margen_minimo"] = {
                "unidades": minimo,
                "pp_por_de": a_pp(minimo),
                "pp_por_de_bruta": a_pp_bruta(minimo),
            }
    return salida


def margenes_en_unidades(sd_identificante: float, margenes_pp: tuple[float, ...] = MARGENES_PP) -> tuple:
    """Los márgenes en pp por DE identificante, traducidos a unidades del regresor."""
    return tuple((pp / 100) / sd_identificante for pp in margenes_pp)
