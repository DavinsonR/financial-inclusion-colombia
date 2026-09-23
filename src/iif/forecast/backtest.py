"""Origen móvil, Diebold-Mariano y la puerta de calidad.

ADR-020 decisión 5: ninguna especificación se publica si no le gana al ingenuo en el
backtest, y la comparación lleva prueba de significancia, no solo diferencia de MAE. Este
módulo es el equivalente de `qa_deposito.py` para la capa de pronóstico: si falla, no se
publica.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from iif.forecast.frame import Marco
from iif.forecast.models import ESPECIFICACIONES, combinar, predecir

REFERENCIA = "ingenuo"
MIN_ENTRENAMIENTO = 12
MIN_COBERTURA = 0.90


def rolling_origin(marco: Marco, primer_origen: int = 2018, h: int = 1,
                   modelos: list[str] | None = None) -> pd.DataFrame:
    """Una fila por (departamento, origen, modelo) con su error en logaritmos.

    Ventana expansiva: se entrena con todo lo anterior al origen, se pronostica, se anota
    el error, se avanza. Cada modelo se reajusta por completo en cada origen.

    `origen` es el primer año que no se vio; con `h > 1` el error es el del año
    `origen + h - 1`, pronosticado a `h` pasos. Antes se anotaba siempre el primer paso
    aunque se pidiera otro horizonte. La varianza del pronóstico viaja en la fila para que
    la cobertura del intervalo se pueda medir con el mismo backtest (`cobertura_intervalo`).
    """
    if h < 1:
        raise ValueError(f"el horizonte tiene que ser al menos 1, no {h}")
    nombres = modelos or ([REFERENCIA] + list(ESPECIFICACIONES) + ["combinacion"])
    filas = []
    for cod in marco.departamentos:
        serie = marco.log_pib[cod]
        for origen in range(primer_origen, marco.anios[-1] + 1):
            entrena = serie.loc[: origen - 1]
            objetivo = origen + h - 1
            if objetivo not in serie.index or len(entrena) < MIN_ENTRENAMIENTO:
                continue
            real = float(serie.loc[objetivo])

            partes = {n: predecir(n, entrena, h) for n in ESPECIFICACIONES}
            for nombre in nombres:
                if nombre == "combinacion":
                    p = combinar(partes)
                elif nombre in partes:
                    p = partes[nombre]
                else:
                    p = predecir(nombre, entrena, h)
                filas.append(dict(dpto_ccdgo=cod, origen=origen, modelo=nombre,
                                  real=real, pronostico=float(p.media[h - 1]),
                                  varianza=float(p.varianza[h - 1]),
                                  error=float(p.media[h - 1] - real) * 100))
    return pd.DataFrame(filas)


def cobertura_intervalo(detalle: pd.DataFrame, nivel: float = 0.80) -> pd.DataFrame:
    """Qué fracción de los valores reales cayó dentro del intervalo publicado, por modelo.

    ADR-022 publica el ancho del intervalo como capa propia; eso solo tiene sentido si el
    intervalo cubre lo que dice. Un 80 % nominal que en el backtest cubre el 65 % comunica
    más confianza de la que el modelo tiene. Las filas sin pronóstico no cuentan ni a favor
    ni en contra: su ausencia ya la castiga la cobertura de `evaluar`.
    """
    if "varianza" not in detalle:
        raise KeyError("el detalle no trae la varianza; vuelve a correr `rolling_origin`")
    z = stats.norm.ppf(0.5 + nivel / 2)
    validas = detalle.dropna(subset=["pronostico", "varianza"])
    semiancho = z * np.sqrt(validas.varianza.to_numpy(dtype=float))
    dentro = (validas.real - validas.pronostico).abs().to_numpy() <= semiancho
    salida = (validas.assign(dentro=dentro)
              .groupby("modelo", sort=False)
              .agg(cobertura_empirica=("dentro", "mean"), n=("dentro", "size")))
    salida["nivel_nominal"] = nivel
    return salida.reset_index()


@dataclass(frozen=True)
class Veredicto:
    modelo: str
    mae: float
    cobertura: float
    ganancia_pct: float | None
    dm_p: float | None
    n: int
    aprobado: bool

    def as_dict(self) -> dict:
        return {
            "modelo": self.modelo, "mae": self.mae, "cobertura": self.cobertura,
            "ganancia_pct": self.ganancia_pct, "dm_p": self.dm_p,
            "n": self.n, "aprobado": self.aprobado,
        }


def diebold_mariano(errores: pd.Series, referencia: pd.Series) -> tuple[float | None, float | None]:
    """Compara dos series de error pareadas por (departamento, origen).

    Prueba sobre la diferencia de errores absolutos. Devuelve la ganancia relativa en MAE
    y el valor p; `None` cuando no hay pares suficientes para decir nada.
    """
    par = pd.concat([errores.rename("m"), referencia.rename("r")], axis=1).dropna()
    if len(par) <= 5:
        return None, None
    mae_ref = par.r.abs().mean()
    if mae_ref == 0:
        return None, None
    ganancia = (1 - par.m.abs().mean() / mae_ref) * 100
    diferencia = par.m.abs() - par.r.abs()
    if diferencia.std(ddof=1) == 0:
        return float(ganancia), None
    return float(ganancia), float(stats.ttest_1samp(diferencia, 0.0).pvalue)


def evaluar(detalle: pd.DataFrame, referencia: str = REFERENCIA) -> list[Veredicto]:
    """MAE, cobertura, ganancia y Diebold-Mariano por modelo, con el veredicto.

    Un modelo queda aprobado si entregó pronóstico en al menos el 90 % de los orígenes y
    le gana al ingenuo. La cobertura no es un detalle: un modelo que revienta en los
    orígenes difíciles y solo responde en los fáciles muestra un MAE bajísimo que no
    significa nada, porque no compitió en las observaciones que importaban.
    """
    ref = detalle[detalle.modelo == referencia].set_index(["dpto_ccdgo", "origen"]).error
    veredictos = []
    for nombre, g in detalle.groupby("modelo", sort=False):
        e = g.error.dropna()
        cobertura = len(e) / len(g) if len(g) else 0.0
        if nombre == referencia:
            veredictos.append(Veredicto(nombre, float(e.abs().mean()), cobertura,
                                        None, None, len(e), True))
            continue
        ganancia, p = diebold_mariano(g.set_index(["dpto_ccdgo", "origen"]).error, ref)
        aprobado = bool(cobertura >= MIN_COBERTURA and ganancia is not None and ganancia > 0)
        veredictos.append(Veredicto(nombre, float(e.abs().mean()) if len(e) else float("nan"),
                                    cobertura, ganancia, p, len(e), aprobado))
    return sorted(veredictos, key=lambda v: (not v.aprobado, v.mae))


def por_regimen(detalle: pd.DataFrame, atipicos=(2020, 2021)) -> dict[str, list[dict]]:
    """El mismo veredicto partido en calma y ruptura.

    El promedio de muestra completa esconde que ninguna especificación domina en los dos
    regímenes, y esa es justamente la evidencia que sostiene combinar en vez de elegir.
    """
    salida = {}
    for etiqueta, sub in (("calma", detalle[~detalle.origen.isin(atipicos)]),
                          ("ruptura", detalle[detalle.origen.isin(atipicos)])):
        if sub.empty:
            continue
        salida[etiqueta] = [v.as_dict() for v in evaluar(sub)]
    return salida


class PuertaDeCalidad(RuntimeError):
    """El pronóstico no se publica porque no supera al ingenuo."""


def exigir_aprobacion(veredictos: list[Veredicto], modelo: str = "combinacion") -> Veredicto:
    """Levanta si el modelo que se va a publicar no pasó la puerta (ADR-020 decisión 5)."""
    encontrado = next((v for v in veredictos if v.modelo == modelo), None)
    if encontrado is None:
        raise PuertaDeCalidad(f"{modelo} no aparece en el backtest")
    if not encontrado.aprobado:
        raise PuertaDeCalidad(
            f"{modelo} no supera al ingenuo: ganancia={encontrado.ganancia_pct}, "
            f"cobertura={encontrado.cobertura:.2f}. No se publica.")
    return encontrado
