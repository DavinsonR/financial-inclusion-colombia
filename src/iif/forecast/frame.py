"""El marco de datos del pronóstico y la vintage que lo acompaña.

ADR-019 decisión 3 obliga a registrar, en cada corrida, con qué versión de los datos se
hizo. El DANE publica 2024 como provisional y 2025 como preliminar, y los va a revisar;
sin la vintage, la revisión contamina retroactivamente cualquier histórico de desempeño y
el backtest deja de valer dentro de un año.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from iif import config

PIB_DEPARTAMENTO = config.DATA_INTERIM / "dane" / "pib_departamento_anual.parquet"
POBLACION_DEPARTAMENTO = config.DATA_INTERIM / "dane" / "poblacion_departamento_anual.parquet"

CODIGO_NACIONAL = "00"
ANIOS_ATIPICOS = (2020, 2021)


@dataclass(frozen=True)
class Vintage:
    """Qué datos vio esta corrida. Va dentro del JSON publicado."""

    archivo: str
    sha256: str
    anio_minimo: int
    anio_maximo: int
    n_departamentos: int
    estado_por_anio: dict[int, str] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "archivo": self.archivo,
            "sha256": self.sha256,
            "anio_minimo": self.anio_minimo,
            "anio_maximo": self.anio_maximo,
            "n_departamentos": self.n_departamentos,
            "estado_por_anio": {str(k): v for k, v in sorted(self.estado_por_anio.items())},
        }


def _sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as fh:
        for bloque in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


@dataclass(frozen=True)
class Marco:
    """Panel departamental en logaritmos, más el total nacional y la vintage."""

    log_pib: pd.DataFrame          # índice anio, columnas dpto_ccdgo
    pib_nivel: pd.DataFrame        # lo mismo sin logaritmo, en miles de millones
    nacional: pd.Series            # total nacional publicado por el DANE
    nombres: dict[str, str]
    vintage: Vintage

    @property
    def anios(self) -> list[int]:
        return list(self.log_pib.index)

    @property
    def departamentos(self) -> list[str]:
        return list(self.log_pib.columns)


def _sin_duplicados(bruto: pd.DataFrame, ruta: Path) -> None:
    """Una fila por departamento y año, o nada.

    `pivot_table` promedia en silencio las filas repetidas: un parquet con dos versiones del
    mismo año daría un PIB que el DANE nunca publicó, y el modelo lo usaría sin quejarse.
    """
    repetidas = bruto.duplicated(["dpto_ccdgo", "anio"], keep=False)
    if repetidas.any():
        ejemplos = bruto.loc[repetidas, ["dpto_ccdgo", "anio"]].drop_duplicates().head(5)
        raise ValueError(f"{ruta.name} repite departamento y año: {ejemplos.values.tolist()}")


def load_frame(ruta: Path | None = None) -> Marco:
    """Lee el PIB departamental real y lo deja listo para modelar.

    Se trabaja en logaritmos porque la varianza del crecimiento es más estable ahí, y se
    conserva el nivel aparte porque la restricción de agregación de ADR-021 es aditiva en
    niveles, no en logaritmos: la suma de los 33 departamentos da el total nacional en
    miles de millones, no en log.
    """
    ruta = ruta or PIB_DEPARTAMENTO
    if not ruta.exists():
        raise FileNotFoundError(f"falta {ruta}; corre `uv run iif parse dane`")

    bruto = pd.read_parquet(ruta)
    _sin_duplicados(bruto, ruta)
    dep = bruto[bruto.dpto_ccdgo != CODIGO_NACIONAL]
    nac = (bruto[bruto.dpto_ccdgo == CODIGO_NACIONAL]
           .set_index("anio")["pib_constante_2015_mm"].sort_index())

    nivel = dep.pivot_table(index="anio", columns="dpto_ccdgo",
                            values="pib_constante_2015_mm").sort_index()
    if nivel.isna().any().any():
        faltan = int(nivel.isna().sum().sum())
        raise ValueError(f"el panel tiene {faltan} huecos; el pronóstico exige panel completo")

    estados = (bruto[bruto.dpto_ccdgo != CODIGO_NACIONAL]
               .groupby("anio")["estado_dato"].agg(lambda s: s.mode().iat[0]))

    return Marco(
        log_pib=np.log(nivel),
        pib_nivel=nivel,
        nacional=nac,
        nombres=dict(dep.drop_duplicates("dpto_ccdgo")[["dpto_ccdgo", "departamento"]].values),
        vintage=Vintage(
            archivo=str(ruta.relative_to(config.REPO_ROOT)),
            sha256=_sha256(ruta),
            anio_minimo=int(nivel.index.min()),
            anio_maximo=int(nivel.index.max()),
            n_departamentos=int(nivel.shape[1]),
            estado_por_anio={int(a): str(e) for a, e in estados.items()},
        ),
    )


def poblacion(ruta: Path | None = None) -> pd.DataFrame:
    """Proyecciones de población total por departamento, hasta 2050.

    ADR-019 decisión 2: el per cápita sale por división, no se modela. Estas cifras son un
    dato del DANE, no un pronóstico de este proyecto, y conviene no confundirlos.
    """
    ruta = ruta or POBLACION_DEPARTAMENTO
    if not ruta.exists():
        raise FileNotFoundError(f"falta {ruta}; corre `uv run iif parse dane`")
    bruto = pd.read_parquet(ruta)
    total = bruto[bruto.area == "total"]
    _sin_duplicados(total, ruta)
    return total.pivot_table(index="anio", columns="dpto_ccdgo", values="poblacion").sort_index()


def dummies_atipicos(anios) -> np.ndarray:
    """Una columna por año atípico declarado (ADR-020).

    Fijadas por nombre a propósito: un detector automático con 20 observaciones marcaría
    también años que son ciclo y no ruptura, y su umbral sería otro hiperparámetro que
    ajustar mirando el error.
    """
    a = np.asarray(list(anios), dtype=int)
    return np.column_stack([(a == anio).astype(float) for anio in ANIOS_ATIPICOS])
