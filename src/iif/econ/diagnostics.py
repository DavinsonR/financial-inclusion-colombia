"""Pruebas sobre los residuos: dependencia entre departamentos, raíces unitarias y dependencia espacial.

Un panel corto y ancho —33 unidades, 8 años— tiene dos problemas antes que ninguno. El primero es que los
departamentos no son independientes: comparten política monetaria, tipo de cambio y pandemia. El segundo es
que lo que parece una relación puede ser dos series con la misma tendencia. Estas pruebas los miden en vez
de suponerlos.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


def pesaran_cd(residuos: pd.DataFrame) -> dict:
    """Prueba CD de Pesaran (2004) de dependencia transversal.

    Promedia las correlaciones por pares de los residuos entre unidades. Bajo la nula de independencia el
    estadístico es normal estándar; un valor grande dice que el error de un departamento sabe algo del
    error de otro en el mismo año, y entonces el error estándar agrupado por departamento se queda corto.
    """
    x = residuos.dropna(axis=1, how="all")
    n = x.shape[1]
    if n < 2:
        return {"estadistico": float("nan"), "p": float("nan"), "n_unidades": n, "rho_medio": float("nan")}
    corr = x.corr(min_periods=3)
    triangulo = corr.to_numpy()[np.triu_indices(n, k=1)]
    triangulo = triangulo[~np.isnan(triangulo)]
    if triangulo.size == 0:
        return {"estadistico": float("nan"), "p": float("nan"), "n_unidades": n, "rho_medio": float("nan")}
    t_medio = float(x.notna().sum().mean())
    cd = np.sqrt(2 * t_medio / (n * (n - 1))) * triangulo.sum()
    return {
        "estadistico": float(cd),
        "p": float(2 * (1 - stats.norm.cdf(abs(cd)))),
        "n_unidades": int(n),
        "rho_medio": float(triangulo.mean()),
        "pares": int(triangulo.size),
    }


def _adf_sin_tendencia(serie: np.ndarray, medias: np.ndarray) -> float:
    """Regresión CADF de una unidad: Δy sobre y rezagado y las medias transversales.

    Es el corazón de CIPS: al meter la media transversal del nivel y de la diferencia se absorbe el factor
    común, que es justo la tendencia nacional que haría parecer no estacionaria a cualquier serie.
    """
    y = np.asarray(serie, dtype=float)
    if np.isnan(y).any() or y.size < 4:
        return float("nan")
    dy = np.diff(y)
    y_rez = y[:-1]
    m_niv = medias[:-1]
    m_dif = np.diff(medias)
    X = np.column_stack([np.ones_like(y_rez), y_rez, m_niv, m_dif])
    if np.linalg.matrix_rank(X) < X.shape[1]:
        return float("nan")
    beta, *_ = np.linalg.lstsq(X, dy, rcond=None)
    resid = dy - X @ beta
    gl = dy.size - X.shape[1]
    if gl <= 0:
        return float("nan")
    s2 = float(resid @ resid) / gl
    xtx_inv = np.linalg.pinv(X.T @ X)
    se = np.sqrt(s2 * xtx_inv[1, 1])
    return float(beta[1] / se) if se > 0 else float("nan")


def cips(niveles: pd.DataFrame) -> dict:
    """Prueba CIPS de raíz unitaria de panel con dependencia transversal (Pesaran, 2007).

    Con T = 8 la prueba tiene poca potencia y el valor crítico tabulado no cubre este caso: por eso el
    resultado se publica como indicio y no como veredicto, y con su T al lado.
    """
    x = niveles.dropna(axis=1, how="all")
    medias = x.mean(axis=1).to_numpy()
    t_barra = [_adf_sin_tendencia(x[col].to_numpy(), medias) for col in x.columns]
    validos = [v for v in t_barra if np.isfinite(v)]
    if not validos:
        return {"cips": float("nan"), "unidades": 0, "periodos": int(x.shape[0])}
    return {
        "cips": float(np.mean(validos)),
        "unidades": int(len(validos)),
        "periodos": int(x.shape[0]),
        "nota": "T corto: la prueba se lee como indicio, no como veredicto",
    }


def vecinos_desde_topojson(ruta: Path | str) -> dict[str, list[str]]:
    """Contigüidad de los departamentos leída de los arcos compartidos del TopoJSON.

    TopoJSON guarda cada frontera una sola vez y la comparte entre las dos unidades que la tienen: dos
    departamentos son vecinos si comparten un arco. No hace falta geometría ni una biblioteca espacial,
    y el resultado es exacto por construcción, no una tolerancia de distancia.
    """
    topo = json.loads(Path(ruta).read_text(encoding="utf-8"))
    objeto = next(iter(topo["objects"].values()))

    def arcos_de(geom: dict) -> set[int]:
        salida: set[int] = set()

        def recorrer(nodo):
            if isinstance(nodo, int):
                salida.add(nodo if nodo >= 0 else ~nodo)
            elif isinstance(nodo, list):
                for hijo in nodo:
                    recorrer(hijo)

        recorrer(geom.get("arcs", []))
        return salida

    por_unidad = {g["properties"]["id"]: arcos_de(g) for g in objeto["geometries"]}
    vecinos: dict[str, list[str]] = {k: [] for k in por_unidad}
    claves = list(por_unidad)
    for i, a in enumerate(claves):
        for b in claves[i + 1 :]:
            if por_unidad[a] & por_unidad[b]:
                vecinos[a].append(b)
                vecinos[b].append(a)
    return vecinos


def matriz_pesos(unidades: list[str], vecinos: dict[str, list[str]]) -> np.ndarray:
    """Matriz de contigüidad normalizada por filas.

    Las islas —el archipiélago no toca a nadie— quedan con fila de ceros: no aportan al estadístico en vez
    de inventarles un vecino, que es la alternativa habitual y la que ensucia el resultado.
    """
    idx = {u: i for i, u in enumerate(unidades)}
    W = np.zeros((len(unidades), len(unidades)))
    for u, vs in vecinos.items():
        if u not in idx:
            continue
        for v in vs:
            if v in idx:
                W[idx[u], idx[v]] = 1.0
    filas = W.sum(axis=1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        W = np.where(filas > 0, W / filas, 0.0)
    return W


def moran_i(valores: np.ndarray, W: np.ndarray, *, permutaciones: int = 999, semilla: int = 20260907) -> dict:
    """I de Moran con inferencia por permutación.

    La inferencia es por permutación y no por la fórmula analítica porque con 33 unidades la aproximación
    normal del estadístico no es de fiar, y permutar las etiquetas es exactamente la hipótesis nula que
    interesa: que el valor de un departamento no tiene nada que ver con el de sus vecinos.
    """
    z = np.asarray(valores, dtype=float)
    ok = np.isfinite(z)
    z, W = z[ok], W[np.ix_(ok, ok)]
    z = z - z.mean()
    denom = float(z @ z)
    if denom == 0 or W.sum() == 0:
        return {"I": float("nan"), "p": float("nan"), "n": int(z.size)}
    observado = float(z @ (W @ z)) / denom
    rng = np.random.default_rng(semilla)
    nulos = np.empty(permutaciones)
    for k in range(permutaciones):
        s = rng.permutation(z)
        nulos[k] = float(s @ (W @ s)) / float(s @ s)
    p = (np.sum(np.abs(nulos) >= abs(observado)) + 1) / (permutaciones + 1)
    return {
        "I": observado,
        "p": float(p),
        "n": int(z.size),
        "esperado": float(-1 / (z.size - 1)),
        "permutaciones": permutaciones,
    }
