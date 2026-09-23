"""Las especificaciones y su combinación.

ADR-020 decisión 3: se publica una combinación, no una especificación única. La razón está
medida y es que ninguna domina en todos los regímenes: con atípicos declarados gana tras la
ruptura, la deriva simple gana en calma, y en el año del choque no gana nadie. Promediar es
más estable que elegir el ganador de un backtest con ocho orígenes.

Todo devuelve `Pronostico`: media y varianza en logaritmos. El intervalo se construye al
final, una sola vez, para que no haya dos formas distintas de calcularlo en el módulo.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from iif.forecast.frame import dummies_atipicos


@dataclass(frozen=True)
class Pronostico:
    """Media y varianza en logaritmos, por horizonte."""

    media: np.ndarray
    varianza: np.ndarray

    def intervalo(self, nivel: float = 0.80) -> tuple[np.ndarray, np.ndarray]:
        z = stats.norm.ppf(0.5 + nivel / 2)
        ancho = z * np.sqrt(self.varianza)
        return self.media - ancho, self.media + ancho


# ------------------------------------------------------------------ referencias

def naive(serie: pd.Series, h: int) -> Pronostico:
    """El último crecimiento observado, repetido. La referencia contra la que se mide todo."""
    d = serie.diff().dropna()
    media = serie.iloc[-1] + d.iloc[-1] * np.arange(1, h + 1)
    var = d.var(ddof=1) * np.arange(1, h + 1)
    return Pronostico(np.asarray(media, float), np.asarray(var, float))


def drift(serie: pd.Series, h: int) -> Pronostico:
    """Deriva de la media histórica. En calma le gana a todo lo demás (ADR-020)."""
    d = serie.diff().dropna()
    media = serie.iloc[-1] + d.mean() * np.arange(1, h + 1)
    var = d.var(ddof=1) * np.arange(1, h + 1)
    return Pronostico(np.asarray(media, float), np.asarray(var, float))


# ------------------------------------------------------------------ Box-Jenkins

def arima(serie: pd.Series, h: int, order: tuple[int, int, int],
          atipicos: bool = True) -> Pronostico:
    """ARIMA sobre el logaritmo del PIB, con los atípicos de ADR-020 como exógenas.

    `trend="t"` y no `"c"`: en un modelo con `d=1` la tendencia lineal se convierte en
    deriva al diferenciar, que es lo que se quiere, y statsmodels rechaza `"c"` cuando hay
    integración.
    """
    from statsmodels.tsa.arima.model import ARIMA

    anios_futuros = [int(serie.index[-1]) + k for k in range(1, h + 1)]
    exog = dummies_atipicos(serie.index) if atipicos else None
    exog_fut = dummies_atipicos(anios_futuros) if atipicos else None

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ajuste = ARIMA(serie.to_numpy(float), order=order, trend="t", exog=exog).fit()
        salida = ajuste.get_forecast(h, exog=exog_fut)
    return Pronostico(np.asarray(salida.predicted_mean, float),
                      np.asarray(salida.var_pred_mean, float))


# Las cuatro que el backtest de ADR-020 dejó por encima del ingenuo, más la deriva, que
# es la que gana entre 2022 y 2025.
ESPECIFICACIONES: dict[str, dict] = {
    "arima_110_atipicos": dict(order=(1, 1, 0), atipicos=True),
    "arima_111_atipicos": dict(order=(1, 1, 1), atipicos=True),
    "arima_011_atipicos": dict(order=(0, 1, 1), atipicos=True),
    "arima_210_atipicos": dict(order=(2, 1, 0), atipicos=True),
    "deriva": None,
}

REFERENCIAS: dict[str, object] = {"ingenuo": naive, "deriva": drift}


def predecir(nombre: str, serie: pd.Series, h: int) -> Pronostico:
    """Una especificación por nombre. Devuelve NaN si no converge; solo lanza si el nombre no existe.

    Un nombre mal escrito no es un fallo de convergencia: tragárselo dejaría un modelo con
    cobertura cero en el backtest y un error que no dice de dónde viene.
    """
    if nombre not in ESPECIFICACIONES and nombre not in REFERENCIAS:
        raise KeyError(f"especificación desconocida: {nombre!r}")
    try:
        if nombre == "ingenuo":
            return naive(serie, h)
        if nombre == "deriva":
            return drift(serie, h)
        cfg = ESPECIFICACIONES[nombre]
        salida = arima(serie, h, **cfg)
        if not np.all(np.isfinite(salida.media)) or not np.all(np.isfinite(salida.varianza)):
            raise ValueError("pronóstico no finito")
        return salida
    except Exception:
        return Pronostico(np.full(h, np.nan), np.full(h, np.nan))


def combinar(partes: dict[str, Pronostico]) -> Pronostico:
    """Media simple de las especificaciones que convergieron.

    La varianza de la combinación es la de una mezcla equiponderada: la media de las
    varianzas más la varianza entre los puntos centrales. El segundo término es el
    desacuerdo entre modelos, y omitirlo publicaría un intervalo más estrecho que la
    incertidumbre real, que es justo lo que ADR-022 prohíbe.
    """
    vivos = [p for p in partes.values() if np.all(np.isfinite(p.media))]
    if not vivos:
        h = len(next(iter(partes.values())).media)
        return Pronostico(np.full(h, np.nan), np.full(h, np.nan))

    medias = np.vstack([p.media for p in vivos])
    varianzas = np.vstack([np.nan_to_num(p.varianza, nan=np.nanmax(p.varianza) if np.any(np.isfinite(p.varianza)) else 0.0)
                           for p in vivos])
    media = medias.mean(axis=0)
    desacuerdo = medias.var(axis=0, ddof=0)
    return Pronostico(media, varianzas.mean(axis=0) + desacuerdo)
