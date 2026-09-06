"""Índice compuesto por PCA (sección 4 del notebook), con la regla de retención y el escalado como opciones.

Novedad respecto al notebook: se calculan y devuelven los pesos implícitos por variable,
que es donde se ve que microcrédito entra con signo negativo.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

try:
    from factor_analyzer.factor_analyzer import calculate_bartlett_sphericity, calculate_kmo

    FA_OK = True
except ImportError:  # pragma: no cover
    FA_OK = False

EPS = 1e-4


@dataclass
class IndexResult:
    scores: pd.DataFrame
    kmo: float
    bartlett: float
    p_bartlett: float
    n_comp: int
    var_pct: np.ndarray
    var_ac: np.ndarray
    eigenvalues: np.ndarray
    pesos: np.ndarray
    loadings: pd.DataFrame
    implied_weights: pd.Series
    corr_orient: float
    retention: str = "variance80"
    scale: str = "minmax_eps"
    extra: dict = field(default_factory=dict)


def _n_components(
    var_ac: np.ndarray, eigenvalues: np.ndarray, retention: str | int, umbral_var: float
) -> int:
    if isinstance(retention, int):
        return retention
    if retention == "variance80":
        return int(np.searchsorted(var_ac, umbral_var)) + 1
    if retention == "kaiser":
        return int(max(1, (eigenvalues > 1).sum()))
    raise ValueError(retention)


def build_pca_index(
    df: pd.DataFrame,
    vars_pca: list[str],
    id_cols: list[str],
    *,
    sign_ref: str = "d_acc_cta_ah",
    umbral_var: float = 80.0,
    retention: str | int = "variance80",
    scale: str = "minmax_eps",
    fit_mask: pd.Series | None = None,
    labels: dict | None = None,
) -> IndexResult:
    datos = df[id_cols + vars_pca].dropna().copy()
    x_raw = datos[vars_pca].values

    kmo_model, chi2_b, p_b = np.nan, np.nan, np.nan
    if FA_OK:
        _, kmo_model = calculate_kmo(x_raw)
        chi2_b, p_b = calculate_bartlett_sphericity(x_raw)

    scaler = StandardScaler()
    if fit_mask is not None:
        m = fit_mask.loc[datos.index] if hasattr(fit_mask, "loc") else fit_mask
        m = np.asarray(m, dtype=bool)
        scaler.fit(x_raw[m])
        x_sc = scaler.transform(x_raw)
        pca = PCA().fit(x_sc[m])
    else:
        x_sc = scaler.fit_transform(x_raw)
        pca = PCA().fit(x_sc)

    scores = pca.transform(x_sc)
    var_pct = pca.explained_variance_ratio_ * 100
    var_ac = np.cumsum(var_pct)
    eigen = pca.explained_variance_
    n_comp = _n_components(var_ac, eigen, retention, umbral_var)

    ret = scores[:, :n_comp].copy()
    comps = pca.components_.copy()
    for k in range(n_comp):
        if np.corrcoef(ret[:, k], datos[sign_ref])[0, 1] < 0:
            ret[:, k] = -ret[:, k]
            comps[k] = -comps[k]

    pesos = var_pct[:n_comp] / var_pct[:n_comp].sum()
    raw = ret @ pesos
    pc1 = ret[:, 0]
    if scale == "minmax_eps":
        datos["IIF_PC1"] = (pc1 - pc1.min()) / (pc1.max() - pc1.min()) + EPS
        iif = (raw - raw.min()) / (raw.max() - raw.min()) + EPS
    elif scale == "standardize":
        datos["IIF_PC1"] = (pc1 - pc1.mean()) / pc1.std(ddof=0)
        iif = (raw - raw.mean()) / raw.std(ddof=0)
    else:
        raise ValueError(scale)
    datos["IIF"] = iif
    datos["log_IIF"] = np.log(iif) if scale == "minmax_eps" else np.nan
    datos["IIF_std"] = (iif - iif.mean()) / iif.std()

    corr_orient = float(np.corrcoef(datos["IIF"], datos[sign_ref])[0, 1])
    labels = labels or {}
    idx = [labels.get(v, v) for v in vars_pca]
    loadings = pd.DataFrame(
        comps[:n_comp].T, index=idx, columns=[f"PC{i + 1} ({var_pct[i]:.1f}%)" for i in range(n_comp)]
    )
    implied = pd.Series(pesos @ comps[:n_comp], index=idx, name="peso_implicito")
    return IndexResult(
        scores=datos,
        kmo=float(kmo_model),
        bartlett=float(chi2_b),
        p_bartlett=float(p_b),
        n_comp=n_comp,
        var_pct=var_pct,
        var_ac=var_ac,
        eigenvalues=eigen,
        pesos=pesos,
        loadings=loadings,
        implied_weights=implied,
        corr_orient=corr_orient,
        retention=str(retention),
        scale=scale,
    )
