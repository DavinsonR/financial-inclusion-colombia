"""Lo que a un nulo le falta para decir algo: qué efecto podría esconder y cuáles descarta.

Un contraste que no rechaza la nula no distingue entre "el efecto es cero" y "este diseño no lo vería
aunque existiera". La cifra que separa las dos lecturas es el efecto mínimo detectable, y depende del error
estándar, no del coeficiente: por eso se puede calcular y por eso es informativo, al contrario que la
llamada potencia retrospectiva, que es una transformación monótona del p-valor y no aporta nada (ADR-018).

La segunda pieza es la prueba de equivalencia. El p-valor responde "¿puedo descartar que el efecto sea
exactamente cero?", que casi nunca es la pregunta. El TOST responde "¿puedo descartar que el efecto sea
mayor que este tamaño?", que es la que un lector hace de verdad.
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


def mde(se: float, *, potencia: float = 0.80, alfa: float = 0.05) -> float:
    """Efecto mínimo detectable: el coeficiente más pequeño que este diseño rechazaría con esa potencia.

    Es la suma de dos valores críticos por el error estándar: uno para no confundir ruido con señal
    (`alfa`, dos colas) y otro para que la señal caiga del lado correcto con la frecuencia que se pide
    (`potencia`, una cola). Con alfa de 0,05 y potencia de 0,80 el factor es 2,802.
    """
    if not np.isfinite(se) or se <= 0:
        return float("nan")
    return float((stats.norm.ppf(1 - alfa / 2) + stats.norm.ppf(potencia)) * se)


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


def escala_del_regresor(
    df: pd.DataFrame,
    x: str,
    controles: list[str] | None = None,
    *,
    unidad: str = "dpto_ccdgo",
    tiempo: str = "anio",
) -> dict:
    """Cuánta variación del regresor sobrevive a los efectos fijos, que es la que identifica el coeficiente.

    Un coeficiente se interpreta por desviación típica del regresor, y en un panel con efectos fijos hay
    dos desviaciones muy distintas: la del regresor tal como se mide y la que queda después de quitar lo
    que es permanente de cada unidad y común de cada año. Publicar el MDE en la primera exagera el diseño;
    publicarlo solo en la segunda esconde cuánta variación se tiró. Van las dos.
    """
    controles = list(controles or [])
    datos = df.dropna(subset=[x, *controles, unidad, tiempo]).reset_index(drop=True)
    bruta = float(datos[x].std(ddof=1))

    solo_unidad = datos[x] - datos.groupby(unidad)[x].transform("mean")
    dos_vias = demean_two_way(datos, [x], unidad, tiempo)[:, 0]

    if controles:
        Z = demean_two_way(datos, [x, *controles], unidad, tiempo)
        objetivo, regresores = Z[:, 0], Z[:, 1:]
        beta, *_ = np.linalg.lstsq(regresores, objetivo, rcond=None)
        identificante = objetivo - regresores @ beta
    else:
        identificante = dos_vias

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


def grados_de_libertad(n: int, unidades: int, periodos: int, regresores: int) -> int:
    """Los que quedan tras absorber un intercepto por unidad y otro por periodo, menos uno por colinealidad."""
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
) -> dict:
    """El bloque de potencia que `resultados.json` publica al lado del coeficiente (ADR-018).

    Todo se calcula sobre la estimación que se le pasa: si la especificación cambia, el error estándar
    cambia y el MDE cambia con él. Ninguna de estas cifras se escribe a mano en ningún sitio.
    """
    controles = list(controles or [])
    escala = escala_del_regresor(df, x, controles, unidad=unidad, tiempo=tiempo)
    sd = escala["de_identificante"]
    gl = grados_de_libertad(estimacion.n, estimacion.unidades, estimacion.periodos, 1 + len(controles))

    def a_pp(valor: float) -> float:
        """De unidades del índice a puntos porcentuales de crecimiento por desviación identificante."""
        return float(valor * sd * 100)

    mde80, mde50 = mde(estimacion.se, potencia=0.80), mde(estimacion.se, potencia=0.50)
    return {
        "escala_del_regresor": escala,
        "grados_de_libertad": gl,
        "mde": {
            "potencia_80": mde80,
            "potencia_80_pp_por_de": a_pp(mde80),
            "potencia_50": mde50,
            "potencia_50_pp_por_de": a_pp(mde50),
            "potencia_80_pp_por_de_bruta": float(mde80 * escala["de_bruta"] * 100),
        },
        "intervalo": {
            "ic95": [estimacion.ic_bajo, estimacion.ic_alto],
            "ic95_pp_por_de": [a_pp(estimacion.ic_bajo), a_pp(estimacion.ic_alto)],
        },
        # El margen se pide en puntos porcentuales, que es la unidad en la que se piensa el efecto, y se
        # traduce a unidades del índice para contrastarlo contra el coeficiente.
        "equivalencia": [
            {**tost(estimacion.coef, estimacion.se, (pp / 100) / sd, gl), "margen_pp_por_de": float(pp)}
            for pp in margenes_pp
            if sd > 0
        ],
    }
