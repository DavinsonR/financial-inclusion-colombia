"""Anclaje al consenso nacional y reparto del desajuste (ADR-021).

Dos cosas que conviene no perder de vista al leer este módulo:

  - **La jerarquía es aditiva en niveles, no en logaritmos.** Los modelos viven en log,
    donde la varianza del crecimiento es estable; la reconciliación ocurre después de
    exponenciar.
  - **El reparto es proporcional al tamaño, no MinT.** Medido sobre ocho orígenes con
    ancla perfecta: proporcional +41,2 % sobre el abajo-arriba, MinT diagonal +21,3 %. El
    método simple gana por el doble, porque MinT con pesos diagonales reparte según la
    varianza en niveles, que escala con el cuadrado del tamaño y carga el ajuste sobre los
    departamentos grandes más de lo que les corresponde.

El anclaje no es gratis: importa el error de pronóstico de un tercero. El punto de
equilibrio medido está en unos 3,5 puntos porcentuales de error del consenso. Por eso
`run.py` publica también la versión sin anclar.

**Una propiedad del reparto proporcional que conviene tener presente al leer el mapa.**
Repartir en proporción al tamaño equivale a multiplicar todos los departamentos por el
mismo escalar, así que la reconciliación **no altera el patrón espacial ni el orden**: solo
desplaza el nivel común. En la corrida publicada el ancla baja el crecimiento de 2026 de los
33 departamentos entre 0,82 (Casanare) y 0,86 puntos (Meta), prácticamente lo mismo a todos;
el rango sale en `resultados.json`, bloque `reconciliacion`, y lo fija una prueba. Dicho de
otro modo, la proyección es un escenario condicional al ancla: el ancla decide cuán intenso se
ve el mapa entero, no qué departamento se ve mejor que cuál.
Quien quiera que el ancla redistribuya entre unidades necesita otro método, y MinT es el
candidato natural — que aquí pierde por el doble de margen.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Ancla:
    """El consenso nacional al que se ancla, con su procedencia.

    `fuente` y `fecha_corte` no son decorado: un mapa anclado sin decir a qué está anclado
    atribuye a su autor la visión de otro (ADR-021 decisión 4).
    """

    fuente: str
    fecha_corte: str
    crecimiento: dict[int, float]      # año -> crecimiento real esperado, en %
    escenario: str = "central"

    def niveles(self, nivel_base: float, anio_base: int, anios: list[int]) -> dict[int, float]:
        """Del crecimiento esperado al nivel del PIB nacional, año a año."""
        salida, actual = {}, nivel_base
        for anio in anios:
            if anio <= anio_base:
                continue
            g = self.crecimiento.get(anio)
            if g is None:
                raise KeyError(f"el ancla {self.fuente} no cubre {anio}")
            actual = actual * (1 + g / 100)
            salida[anio] = actual
        return salida

    def as_dict(self) -> dict:
        return {"fuente": self.fuente, "fecha_corte": self.fecha_corte,
                "escenario": self.escenario,
                "crecimiento": {str(k): v for k, v in sorted(self.crecimiento.items())}}


def coherencia(pib_nivel: pd.DataFrame, nacional: pd.Series) -> pd.Series:
    """Brecha entre la suma de los departamentos y el total nacional, en %.

    Es exacta desde 2013 (≤0,06 %) y no antes: en los años retropolados a base 2015 el
    DANE no impone suma exacta y la brecha llega a 1,28 % en 2009. Afecta al tramo más
    antiguo del entrenamiento, no a la ventana donde se reconcilia.
    """
    suma = pib_nivel.sum(axis=1)
    comun = suma.index.intersection(nacional.index)
    return ((suma.loc[comun] / nacional.loc[comun]) - 1) * 100


def reparto_proporcional(base: np.ndarray, objetivo: float) -> np.ndarray:
    """Lleva la suma de `base` a `objetivo` repartiendo la diferencia según el peso.

    El resultado suma exactamente `objetivo` salvo error de redondeo de punto flotante.

    Falla en vez de devolver `base` sin tocar. Antes, un objetivo no finito o una suma no
    positiva dejaban pasar el pronóstico sin anclar con la etiqueta de reconciliado, y un
    departamento sin pronóstico (NaN) convertía en NaN a los 33 sin avisar.
    """
    base = np.asarray(base, dtype=float)
    if not np.all(np.isfinite(base)):
        raise ValueError(f"la base a reconciliar tiene {int((~np.isfinite(base)).sum())} valores no finitos")
    if not np.isfinite(objetivo):
        raise ValueError(f"el objetivo de la reconciliación no es finito: {objetivo}")
    suma = base.sum()
    if suma <= 0:
        raise ValueError(f"la base suma {suma}; el reparto proporcional necesita una suma positiva")
    return base + (objetivo - suma) * (base / suma)


def reparto_mint_diagonal(base: np.ndarray, varianza_log: np.ndarray,
                          objetivo: float) -> np.ndarray:
    """MinT con pesos diagonales. Se conserva para que la comparación de ADR-021 se pueda repetir.

    No es el método adoptado: pierde contra el reparto proporcional por el doble de
    margen. Está aquí porque una decisión medida debe poder volver a medirse.
    """
    base = np.asarray(base, dtype=float)
    var_nivel = (base ** 2) * np.asarray(varianza_log, dtype=float)
    if not np.all(np.isfinite(var_nivel)):
        raise ValueError("MinT recibió varianzas no finitas; el reparto quedaría en NaN")
    total = var_nivel.sum()
    if total <= 0 or not np.isfinite(objetivo):
        return reparto_proporcional(base, objetivo)
    return base + (objetivo - base.sum()) * (var_nivel / total)


def reconciliar(niveles: pd.DataFrame, objetivo_por_anio: dict[int, float],
                metodo: str = "proporcional",
                varianza_log: pd.DataFrame | None = None) -> pd.DataFrame:
    """Aplica el reparto año a año sobre una matriz año × departamento en niveles."""
    if metodo not in {"proporcional", "mint"}:
        raise ValueError(f"método desconocido: {metodo}")
    salida = niveles.copy()
    for anio, objetivo in objetivo_por_anio.items():
        if anio not in salida.index:
            continue
        fila = salida.loc[anio].to_numpy(dtype=float)
        if metodo == "proporcional":
            salida.loc[anio] = reparto_proporcional(fila, objetivo)
        else:
            if varianza_log is None:
                raise ValueError("MinT necesita la varianza de pronóstico")
            salida.loc[anio] = reparto_mint_diagonal(
                fila, varianza_log.loc[anio].to_numpy(dtype=float), objetivo)
    return salida
