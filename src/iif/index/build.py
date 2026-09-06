"""Construcción del índice: normalizar, estandarizar, un componente por dimensión y promediar (ADR-015)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from iif import config


@dataclass
class DimensionFit:
    """Parámetros congelados de una dimensión: cómo estandarizar y cómo combinar."""

    dimension: str
    metodo: str
    variables: list[str]
    media: dict[str, float]
    desviacion: dict[str, float]
    cargas: dict[str, float]
    varianza_explicada: float | None = None
    kmo: float | None = None
    bartlett_chi2: float | None = None
    bartlett_p: float | None = None


@dataclass
class IndexResult:
    scores: pd.DataFrame
    fits: dict[str, DimensionFit]
    implicitos: pd.DataFrame
    sensibilidad: pd.DataFrame
    correlacion_rangos: pd.DataFrame
    normalizado: pd.DataFrame = field(repr=False, default_factory=pd.DataFrame)


def load_contract(path: Path | None = None) -> dict:
    return config.load_yaml(path or config.CONFIG_DIR / "index.yaml")


def contract_variables(contract: dict) -> list[str]:
    return [v["variable_id"] for d in contract["dimensiones"].values() for v in d["variables"]]


def normalize_panel(
    panel: pd.DataFrame,
    contract: dict,
    unidades: dict[str, str],
    *,
    col_poblacion: str = "poblacion_total",
    col_producto: str = "pib_corriente_mm",
) -> pd.DataFrame:
    """Conteos por 10.000 habitantes y montos como porcentaje del producto (ADR-015, punto 1).

    `unidades` mapea cada variable a 'count' o 'cop' (viene de dim_variable). El producto llega en miles de
    millones de pesos, de ahí el factor 1e9.
    """
    reglas = contract["normalizacion"]
    out = panel.copy()
    poblacion = pd.to_numeric(out[col_poblacion], errors="coerce")
    producto = pd.to_numeric(out[col_producto], errors="coerce") * 1e9
    for v in contract_variables(contract):
        if v not in out.columns:
            raise KeyError(f"el panel no trae la variable {v!r} que exige config/index.yaml")
        unidad = unidades.get(v)
        if unidad is None:
            raise KeyError(f"no se conoce la unidad de {v!r}; debe venir de dim_variable")
        regla = reglas[unidad]
        valor = pd.to_numeric(out[v], errors="coerce")
        if regla == "por_10k_habitantes":
            out[v] = valor / poblacion.replace(0, np.nan) * 10_000
        elif regla == "pct_producto":
            out[v] = valor / producto.replace(0, np.nan) * 100
        else:
            raise ValueError(f"regla de normalización desconocida: {regla!r}")
    return out


def _kmo(corr: np.ndarray) -> float:
    """Kaiser-Meyer-Olkin sobre la matriz de correlación: proporción de correlación no parcial."""
    inv = np.linalg.pinv(corr)
    d = np.sqrt(np.diag(inv))
    parcial = -inv / np.outer(d, d)
    np.fill_diagonal(parcial, 0.0)
    c = corr.copy()
    np.fill_diagonal(c, 0.0)
    return float((c**2).sum() / ((c**2).sum() + (parcial**2).sum()))


def _bartlett(corr: np.ndarray, n: int) -> tuple[float, float]:
    """Prueba de esfericidad: ¿la matriz de correlación difiere de la identidad?"""
    from scipy import stats

    p = corr.shape[0]
    det = np.linalg.det(corr)
    det = max(det, 1e-300)
    chi2 = -((n - 1) - (2 * p + 5) / 6) * np.log(det)
    gl = p * (p - 1) / 2
    return float(chi2), float(stats.chi2.sf(chi2, gl))


def fit_dimension(calib: pd.DataFrame, dimension: str, spec: dict, *, min_obs: int = 20) -> DimensionFit:
    """Estima media, desviación y cargas de una dimensión sobre la ventana de calibración."""
    variables = [v["variable_id"] for v in spec["variables"]]
    signos = {v["variable_id"]: v.get("signo_esperado", 1) for v in spec["variables"]}
    x = calib[variables].apply(pd.to_numeric, errors="coerce").dropna()
    if len(x) < min_obs:
        raise ValueError(
            f"{dimension}: solo {len(x)} observaciones completas en la calibración, se exigen {min_obs}"
        )
    media = x.mean()
    desv = x.std(ddof=1).replace(0, np.nan)
    if desv.isna().any():
        raise ValueError(
            f"{dimension}: variables sin variación en la calibración: {list(desv[desv.isna()].index)}"
        )
    z = (x - media) / desv

    if spec["metodo"] == "pesos_iguales":
        # Cada variable pesa 1/k dentro de la dimensión. No exige estructura factorial y no puede dar un
        # peso negativo a una variable que debe sumar (ADR-015, adenda).
        corr = np.corrcoef(z.to_numpy(), rowvar=False)
        chi2, p_val = _bartlett(corr, len(z))
        cargas = {v: float(signos[v]) / len(variables) for v in variables}
        return DimensionFit(
            dimension,
            "pesos_iguales",
            variables,
            media.to_dict(),
            desv.to_dict(),
            cargas,
            kmo=_kmo(corr),
            bartlett_chi2=chi2,
            bartlett_p=p_val,
        )

    if spec["metodo"] == "variable_unica":
        if len(variables) != 1:
            raise ValueError(f"{dimension}: el método variable_unica exige exactamente una variable")
        v = variables[0]
        return DimensionFit(
            dimension, "variable_unica", variables, media.to_dict(), desv.to_dict(), {v: float(signos[v])}
        )

    corr = np.corrcoef(z.to_numpy(), rowvar=False)
    kmo = _kmo(corr)
    chi2, p_val = _bartlett(corr, len(z))
    # Componente principal: primer vector propio de la matriz de correlación de las estandarizadas.
    valores, vectores = np.linalg.eigh(corr)
    orden = np.argsort(valores)[::-1]
    valores, vectores = valores[orden], vectores[:, orden]
    carga = vectores[:, 0]
    # Orientación: el signo del componente es arbitrario, así que se fija con el signo esperado de la
    # variable de mayor carga absoluta. Sin esto el índice podría salir invertido de una corrida a otra.
    ancla = int(np.argmax(np.abs(carga)))
    if np.sign(carga[ancla]) != np.sign(signos[variables[ancla]]):
        carga = -carga
    # Se escala para que el score tenga varianza 1 en la calibración.
    carga = carga / np.sqrt(valores[0])
    return DimensionFit(
        dimension,
        "pca",
        variables,
        media.to_dict(),
        desv.to_dict(),
        dict(zip(variables, carga.astype(float), strict=True)),
        varianza_explicada=float(valores[0] / valores.sum()),
        kmo=kmo,
        bartlett_chi2=chi2,
        bartlett_p=p_val,
    )


def apply_dimension(panel: pd.DataFrame, fit: DimensionFit) -> pd.Series:
    z = pd.DataFrame(
        {
            v: (pd.to_numeric(panel[v], errors="coerce") - fit.media[v]) / fit.desviacion[v]
            for v in fit.variables
        }
    )
    return sum(z[v] * fit.cargas[v] for v in fit.variables)


def pesos_implicitos(fits: dict[str, DimensionFit], pesos_dim: dict[str, float]) -> pd.DataFrame:
    """Peso de cada variable en el compuesto, en la escala estandarizada y en la original (ADR-015, punto 7).

    En la escala original el peso es el de la estandarizada dividido por la desviación de la variable: es
    cuánto mueve el índice un cambio de una unidad de la variable tal como se mide.
    """
    filas = []
    for dim, fit in fits.items():
        w_dim = pesos_dim[dim]
        for v in fit.variables:
            filas.append(
                {
                    "dimension": dim,
                    "variable_id": v,
                    "peso_estandarizado": w_dim * fit.cargas[v],
                    "peso_escala_original": w_dim * fit.cargas[v] / fit.desviacion[v],
                    "desviacion_calibracion": fit.desviacion[v],
                }
            )
    return pd.DataFrame(filas).sort_values(["dimension", "variable_id"]).reset_index(drop=True)


def _sarma(z: pd.DataFrame) -> pd.Series:
    """Índice de distancia de Sarma: 1 menos la distancia euclídea normalizada al vector ideal."""
    x = z.clip(lower=0)
    x = x.div(x.max().replace(0, np.nan), axis=1).fillna(0.0)
    k = x.shape[1]
    d_peor = np.sqrt(k)
    return 1 - np.sqrt(((1 - x) ** 2).sum(axis=1)) / d_peor


def build_index(
    panel: pd.DataFrame,
    unidades: dict[str, str],
    *,
    contract: dict | None = None,
    id_cols: tuple[str, ...] = ("dpto_ccdgo", "anio"),
    col_poblacion: str = "poblacion_total",
    col_producto: str = "pib_corriente_mm",
    pesos_congelados: dict | None = None,
) -> IndexResult:
    """Calcula subíndices y compuesto. Con `pesos_congelados` reproduce exactamente una corrida anterior."""
    contract = contract or load_contract()
    norm = normalize_panel(panel, contract, unidades, col_poblacion=col_poblacion, col_producto=col_producto)

    if pesos_congelados:
        fits = {d: DimensionFit(**f) for d, f in pesos_congelados.items()}
    else:
        c = contract["calibracion"]
        calib = norm[(norm["anio"] >= c["anio_desde"]) & (norm["anio"] <= c["anio_hasta"])]
        fits = {dim: fit_dimension(calib, dim, spec) for dim, spec in contract["dimensiones"].items()}

    pesos_dim = contract["compuesto"]["pesos"]
    scores = norm[list(id_cols)].copy()
    for dim, fit in fits.items():
        scores[f"iif_{dim}"] = apply_dimension(norm, fit)
    scores["dimensiones_observadas"] = sum(scores[f"iif_{d}"].notna().astype(int) for d in fits)
    # El compuesto exige las tres dimensiones: una unidad sin crédito de vivienda observado no tiene
    # profundidad, y rellenarla con cero sería inventar un dato (R-13).
    scores["iif_compuesto"] = sum(scores[f"iif_{d}"] * w for d, w in pesos_dim.items())

    # Sensibilidad: el primer componente principal por dimensión, que es el método que los datos no
    # sostienen (KMO por debajo de 0,5; ADR-015 adenda), y el índice de distancia de Sarma.
    cal = contract["calibracion"]
    calib_sens = norm[(norm["anio"] >= cal["anio_desde"]) & (norm["anio"] <= cal["anio_hasta"])]
    sens = norm[list(id_cols)].copy()
    for dim, spec in contract["dimensiones"].items():
        if len(spec["variables"]) == 1:
            sens[f"pca_{dim}"] = apply_dimension(norm, fits[dim])
        else:
            sens[f"pca_{dim}"] = apply_dimension(
                norm, fit_dimension(calib_sens, dim, {**spec, "metodo": "pca"})
            )
    sens["iif_pca"] = sum(sens[f"pca_{d}"] * w for d, w in pesos_dim.items())
    todas = [v for f in fits.values() for v in f.variables]
    z_todas = pd.DataFrame(
        {
            v: (
                pd.to_numeric(norm[v], errors="coerce")
                - next(f.media[v] for f in fits.values() if v in f.media)
            )
            / next(f.desviacion[v] for f in fits.values() if v in f.desviacion)
            for v in todas
        }
    )
    sens["iif_sarma"] = _sarma(z_todas)

    comp = scores[[*id_cols, "iif_compuesto"]].merge(
        sens[[*id_cols, "iif_pca", "iif_sarma"]], on=list(id_cols)
    )
    corr = comp[["iif_compuesto", "iif_pca", "iif_sarma"]].corr(method="spearman")
    return IndexResult(
        scores=scores,
        fits=fits,
        implicitos=pesos_implicitos(fits, pesos_dim),
        sensibilidad=sens,
        correlacion_rangos=corr,
        normalizado=norm,
    )
