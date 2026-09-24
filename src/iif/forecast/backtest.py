"""Origen móvil, Diebold-Mariano y la puerta de calidad.

ADR-020 decisión 5, corregida por ADR-023: ninguna especificación se publica si no le gana
al ingenuo en el backtest, también sin el origen que más aporta; la prueba de Diebold-Mariano
se agrupa por origen y se publica como información, no como criterio. Este
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
# Por debajo de tres orígenes la t por origen tiene un grado de libertad o ninguno.
MIN_ORIGENES = 3


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
    origenes_ganados: int | None = None
    n_origenes: int | None = None
    mejor_origen: int | None = None
    ganancia_sin_mejor_origen_pct: float | None = None

    def as_dict(self) -> dict:
        return {
            "modelo": self.modelo, "mae": self.mae, "cobertura": self.cobertura,
            "ganancia_pct": self.ganancia_pct, "dm_p": self.dm_p,
            "origenes_ganados": self.origenes_ganados, "n_origenes": self.n_origenes,
            "mejor_origen": self.mejor_origen,
            "ganancia_sin_mejor_origen_pct": self.ganancia_sin_mejor_origen_pct,
            "n": self.n, "aprobado": self.aprobado,
        }


@dataclass(frozen=True)
class PorOrigen:
    """Lo que la comparación dice cuando se lee año por año (ADR-023, decisión 2)."""
    ganados: int
    total: int
    mejor_origen: int
    ganancia_sin_mejor_pct: float | None


def _pares(errores: pd.Series, referencia: pd.Series) -> pd.DataFrame:
    return pd.concat([errores.rename("m"), referencia.rename("r")], axis=1).dropna()


def _ganancia(par: pd.DataFrame) -> float | None:
    mae_ref = par.r.abs().mean()
    if len(par) == 0 or mae_ref == 0:
        return None
    return float((1 - par.m.abs().mean() / mae_ref) * 100)


def diebold_mariano(errores: pd.Series, referencia: pd.Series) -> tuple[float | None, float | None]:
    """Compara dos series de error pareadas por (departamento, origen).

    Devuelve la ganancia relativa en MAE y el valor p de Diebold-Mariano **agrupado por
    origen** (ADR-023): los departamentos de un mismo año comparten el choque, así que la
    prueba t se hace sobre la media por origen de la diferencia de errores absolutos, con
    n − 1 grados de libertad. Tratar los pares como independientes subestimaba el error
    estándar unas 4,5 veces en el panel real (B-065). `None` cuando no hay pares u orígenes
    suficientes para decir nada.
    """
    par = _pares(errores, referencia)
    if len(par) <= 5:
        return None, None
    ganancia = _ganancia(par)
    if ganancia is None:
        return None, None
    diferencia = (par.m.abs() - par.r.abs()).groupby(level="origen").mean()
    if len(diferencia) < MIN_ORIGENES or diferencia.std(ddof=1) == 0:
        return ganancia, None
    return ganancia, float(stats.ttest_1samp(diferencia, 0.0).pvalue)


def por_origen(errores: pd.Series, referencia: pd.Series) -> PorOrigen | None:
    """Orígenes ganados y la ganancia que queda al quitar el origen que más aporta.

    El «mejor origen» es el de diferencia media más negativa: el año en que el modelo le
    saca más ventaja al ingenuo. Si la ganancia desaparece sin él, no había una ventaja
    del modelo sino un año afortunado.
    """
    par = _pares(errores, referencia)
    if par.empty:
        return None
    diferencia = (par.m.abs() - par.r.abs()).groupby(level="origen").mean()
    mejor = int(diferencia.idxmin())
    resto = par[par.index.get_level_values("origen") != mejor]
    return PorOrigen(ganados=int((diferencia < 0).sum()), total=len(diferencia),
                     mejor_origen=mejor, ganancia_sin_mejor_pct=_ganancia(resto))


def evaluar(detalle: pd.DataFrame, referencia: str = REFERENCIA) -> list[Veredicto]:
    """MAE, cobertura, ganancia y Diebold-Mariano por origen, con el veredicto.

    Un modelo queda aprobado (ADR-023, decisión 3) si entregó pronóstico en al menos el
    90 % de los orígenes, le gana al ingenuo en MAE y sigue sin perder al quitar el origen
    que más aporta. El valor p se publica pero no decide: con ocho orígenes la prueba no
    tiene potencia para detectar ni una mejora del 100 %, y una puerta de superioridad
    sería una prohibición permanente.

    La cobertura no es un detalle: un modelo que revienta en los orígenes difíciles y solo
    responde en los fáciles muestra un MAE bajísimo que no significa nada, porque no
    compitió en las observaciones que importaban.
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
        errores = g.set_index(["dpto_ccdgo", "origen"]).error
        ganancia, p = diebold_mariano(errores, ref)
        orig = por_origen(errores, ref)
        sin_mejor = orig.ganancia_sin_mejor_pct if orig else None
        aprobado = bool(cobertura >= MIN_COBERTURA
                        and ganancia is not None and ganancia > 0
                        and sin_mejor is not None and sin_mejor >= 0)
        veredictos.append(Veredicto(
            nombre, float(e.abs().mean()) if len(e) else float("nan"), cobertura, ganancia, p,
            len(e), aprobado,
            origenes_ganados=orig.ganados if orig else None,
            n_origenes=orig.total if orig else None,
            mejor_origen=orig.mejor_origen if orig else None,
            ganancia_sin_mejor_origen_pct=sin_mejor))
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
    """Levanta si el modelo que se va a publicar no pasó la puerta (ADR-020 decisión 5, ADR-023)."""
    encontrado = next((v for v in veredictos if v.modelo == modelo), None)
    if encontrado is None:
        raise PuertaDeCalidad(f"{modelo} no aparece en el backtest")
    if not encontrado.aprobado:
        raise PuertaDeCalidad(
            f"{modelo} no pasa la puerta: ganancia={encontrado.ganancia_pct}, "
            f"sin el origen {encontrado.mejor_origen}={encontrado.ganancia_sin_mejor_origen_pct}, "
            f"cobertura={encontrado.cobertura:.2f}. No se publica.")
    return encontrado
