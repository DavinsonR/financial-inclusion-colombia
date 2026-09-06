"""Panel, rezagos y estimador de efectos fijos (secciones 5–7 del notebook)."""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import pandas as pd
from linearmodels.panel import PanelOLS

from iif.legacy.constants import COL_TIEMPO, CTRL, VARS_LAG


@dataclass
class FitRow:
    label: str
    var: str
    beta: float
    se: float
    p: float
    N: float
    r2: float
    n_clusters: int
    model: object = None

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "var": self.var,
            "beta": self.beta,
            "se": self.se,
            "p": self.p,
            "N": self.N,
            "r2": self.r2,
            "n_clusters": self.n_clusters,
        }


def stars(p: float) -> str:
    return "***" if p < 0.01 else ("**" if p < 0.05 else ("*" if p < 0.10 else ""))


def build_panel(panel: pd.DataFrame) -> pd.DataFrame:
    """Rezagos una sola vez sobre el panel completo, ordenado por fecha; índice (departamento, Fecha)."""
    pm = panel.copy().rename(columns={"d_acc_internet": "internet"})
    pm = pm.sort_values(["departamento", COL_TIEMPO]).reset_index(drop=True)
    for v in VARS_LAG:
        if v in pm.columns:
            for lag in (1, 2):
                pm[f"{v}_lag{lag}"] = pm.groupby("departamento")[v].shift(lag)
    pm["IIF_mean"] = pm.groupby("departamento")["IIF"].transform("mean")
    pm["IIF_within"] = pm["IIF"] - pm["IIF_mean"]
    pm["IIF_lag1_mean"] = pm.groupby("departamento")["IIF_lag1"].transform("mean")
    pm["IIF_lag1_within"] = pm["IIF_lag1"] - pm["IIF_lag1_mean"]
    return pm.set_index(["departamento", COL_TIEMPO])


def sample_trace(pm: pd.DataFrame) -> dict[str, int]:
    trace = {}
    for etiqueta, cols in [
        ("crec_pib + IIF", ["crec_pib", "IIF"]),
        ("crec_pib + IIF_lag1 + crec_pib_lag1", ["crec_pib", "IIF_lag1", "crec_pib_lag1"]),
        ("crec_pib_pc + IIF", ["crec_pib_pc", "IIF"]),
        ("crec_pib_pc + IIF_lag1 + lag DV", ["crec_pib_pc", "IIF_lag1", "crec_pib_pc_lag1"]),
        ("crec_pib_pc + IIF_lag2 + lag DV", ["crec_pib_pc", "IIF_lag2", "crec_pib_pc_lag1"]),
    ]:
        cols_ok = [c for c in cols if c in pm.columns] + CTRL
        trace[etiqueta] = int(len(pm.dropna(subset=cols_ok)))
    return trace


def fit_fe(
    data: pd.DataFrame,
    var_iif: str,
    dv: str,
    *,
    dinamico: bool = True,
    time_effects: bool = False,
    label: str = "",
    cov: str = "clustered",
    extra: list[str] | None = None,
    min_obs: int = 30,
    controls: list[str] | None = None,
) -> FitRow | None:
    """Efectos fijos de entidad, opcionalmente con efectos de tiempo y rezago de la dependiente.

    Con menos de 10 clústeres la inferencia clusterizada no es fiable: se avisa (B-009).
    """
    ctrl = CTRL if controls is None else controls
    dv_lag = f"{dv}_lag1"
    need = [dv, var_iif] + ctrl + ([dv_lag] if dinamico else []) + (extra or [])
    need = [c for c in need if c in data.columns]
    sub = data.dropna(subset=need)
    if len(sub) < min_obs:
        return None
    partes = ([dv_lag] if dinamico else []) + [var_iif] + ctrl + (extra or [])
    formula = (
        f"{dv} ~ " + " + ".join(partes) + " + EntityEffects" + (" + TimeEffects" if time_effects else "")
    )
    mod = PanelOLS.from_formula(formula, data=sub, drop_absorbed=True)
    m = (
        mod.fit(cov_type="kernel")
        if cov == "driscoll-kraay"
        else mod.fit(cov_type="clustered", cluster_entity=True)
    )
    n_clusters = int(sub.index.get_level_values(0).nunique())
    if cov == "clustered" and n_clusters < 10:
        warnings.warn(
            f"{label or var_iif}: solo {n_clusters} clústeres; la inferencia clusterizada no es fiable",
            stacklevel=2,
        )
    return FitRow(
        label=label,
        var=var_iif,
        beta=float(m.params[var_iif]),
        se=float(m.std_errors[var_iif]),
        p=float(m.pvalues[var_iif]),
        N=float(m.nobs),
        r2=float(m.rsquared),
        n_clusters=n_clusters,
        model=m,
    )


def format_row(r: FitRow | None) -> str:
    if r is None:
        return "  (muestra insuficiente)"
    return (
        f"  {r.label:<48} β={r.beta:+9.4f}{stars(r.p):<3} SE={r.se:7.4f} "
        f"p={r.p:.4f} N={r.N:>4.0f} R²={r.r2:.4f}"
    )
