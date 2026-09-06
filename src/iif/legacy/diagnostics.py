"""Diagnósticos del notebook (secciones 8–10): Hausman, Mundlak, Nickell, Pesaran CD, autocorrelación."""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS, RandomEffects
from scipy import stats
from scipy.stats import chi2 as chi2_dist


@dataclass
class HausmanResult:
    chi2: float
    p: float
    df: int
    N: float
    valid: bool
    note: str


def hausman_clustered(sub: pd.DataFrame, formula_rhs: str) -> tuple[HausmanResult, object]:
    """Reproduce el Hausman del notebook. NO es válido: ambos modelos usan covarianza clusterizada,
    así que V_fe - V_re no es definida positiva y `pinv` devuelve un número arbitrario (B-008).
    Se conserva para la reproducción; Mundlak es la alternativa válida."""
    warnings.warn("Hausman con covarianza clusterizada no es un test válido; usar Mundlak", stacklevel=2)
    m_fe = PanelOLS.from_formula(f"crec_pib ~ {formula_rhs} + EntityEffects", data=sub).fit(
        cov_type="clustered", cluster_entity=True
    )
    m_re = RandomEffects.from_formula(f"crec_pib ~ {formula_rhs}", data=sub).fit(
        cov_type="clustered", cluster_entity=True
    )
    comunes = [v for v in m_fe.params.index if v in m_re.params.index]
    diff = m_fe.params[comunes].values - m_re.params[comunes].values
    vd = m_fe.cov.loc[comunes, comunes].values - m_re.cov.loc[comunes, comunes].values
    hst = float(diff @ np.linalg.pinv(vd) @ diff)
    p_h = float(1 - chi2_dist.cdf(hst, df=len(comunes)))
    return HausmanResult(
        hst, p_h, len(comunes), float(m_fe.nobs), False, "covarianza clusterizada: estadístico no válido"
    ), m_fe


def mundlak(sub: pd.DataFrame, formula_rhs: str) -> dict:
    m_mu = RandomEffects.from_formula(f"crec_pib ~ {formula_rhs}", data=sub).fit(
        cov_type="clustered", cluster_entity=True
    )
    return {
        "beta_within": float(m_mu.params["IIF_lag1_within"]),
        "p_within": float(m_mu.pvalues["IIF_lag1_within"]),
        "beta_mean": float(m_mu.params["IIF_lag1_mean"]),
        "p_mean": float(m_mu.pvalues["IIF_lag1_mean"]),
        "N": float(m_mu.nobs),
    }


def between_within_corr(sub: pd.DataFrame, x: str = "IIF", y: str = "crec_pib") -> tuple[float, float]:
    ent = sub.index.get_level_values(0)
    ib = sub[x].groupby(ent).transform("mean")
    pb = sub[y].groupby(ent).transform("mean")
    cb = float(np.corrcoef(ib, pb)[0, 1])
    cw = float(np.corrcoef(sub[x] - ib, sub[y] - pb)[0, 1])
    return cb, cw


def nickell_bias(rho: float, T: int) -> dict:
    """Aproximación de Nickell (1981) para AR(1) con efectos fijos: sesgo ≈ -(1+ρ)/(T-1).
    Solo orientativa: la fórmula supone AR(1) puro sin regresores adicionales (B-011)."""
    sesgo = -(1 + rho) / (T - 1)
    return {
        "rho": rho,
        "T": T,
        "sesgo": sesgo,
        "rho_corregido": rho - sesgo,
        "pct_de_rho": abs(sesgo / rho) * 100 if rho else np.nan,
    }


def pesaran_cd(resids: pd.Series) -> dict:
    """CD de Pesaran (2004) sobre residuos con índice (entidad, tiempo)."""
    resid = resids.unstack(level=0)
    corr = resid.corr()
    n_ = corr.shape[0]
    t_ = float(resid.notna().sum().mean())
    iu = np.triu_indices_from(corr.values, k=1)
    cd = float(np.sqrt(2 * t_ / (n_ * (n_ - 1))) * np.nansum(corr.values[iu]))
    p_cd = float(2 * (1 - stats.norm.cdf(abs(cd))))
    return {"CD": cd, "p": p_cd, "N": int(n_), "T_medio": t_}


def residual_ar1(resids: pd.Series) -> dict:
    """Correlación de residuos con su rezago por entidad. El notebook lo llama Wooldridge; no lo es (B-011)."""
    r = resids.to_frame("e")
    r["e_lag"] = r.groupby(level=0)["e"].shift(1)
    rr = r.dropna()
    rho_e, p_e = stats.pearsonr(rr["e"], rr["e_lag"])
    return {"rho": float(rho_e), "p": float(p_e)}
