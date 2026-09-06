"""Ejecuta el notebook consolidado como una función y devuelve todo en objetos comparables."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from iif.data.scrub import sha256_of
from iif.legacy import diagnostics as dg
from iif.legacy.constants import (
    COL_TIEMPO,
    CTRL,
    LABELS_PCA,
    REGION_LABEL,
    VARS_DESC,
    VARS_PCA,
    VARS_PCA_SIN_INTERNET,
)
from iif.legacy.index import IndexResult, build_pca_index
from iif.legacy.ledger import Ledger
from iif.legacy.load import load_legacy_panel
from iif.legacy.panel import FitRow, build_panel, fit_fe, format_row, sample_trace
from iif.legacy.variables import VariableOptions, build_variables, d1_diagnostics

ID_COLS = ["departamento", COL_TIEMPO]


@dataclass
class LegacyResults:
    mode: str
    env: dict
    d1: dict
    umbral_densidad: float
    frac_cero_crec_pc: float
    index: IndexResult
    index_sin_net: IndexResult
    corr_iif_sin_net: float
    index_oos: IndexResult | None
    corr_iif_oos: float
    trace: dict
    tabla6: dict[str, FitRow | None]
    hausman: dg.HausmanResult | None
    mundlak: dict | None
    corr_between: float
    corr_within: float
    nickell: dict
    robustez: list[FitRow | None]
    pesaran: dict | None
    ar1: dict | None
    dk_vs_cluster: dict | None
    regional: pd.DataFrame
    descriptivas: pd.DataFrame
    tabla2: pd.DataFrame
    ledger: Ledger
    lines: list[str] = field(default_factory=list)

    @property
    def ledger_frame(self) -> pd.DataFrame:
        return self.ledger.to_frame()


def run_legacy_pipeline(
    xlsx_path: Path, mode: str = "notebook", ledger_yaml: Path | None = None
) -> LegacyResults:
    import linearmodels
    import sklearn

    opts = VariableOptions.for_mode(mode)
    ledger = Ledger.from_yaml(ledger_yaml)
    lines: list[str] = []
    say = lines.append
    env = {
        "python": sys.version.split()[0],
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "linearmodels": linearmodels.__version__,
        "sklearn": sklearn.__version__,
        "archivo": Path(xlsx_path).name,
        "sha256": sha256_of(Path(xlsx_path)),
        "modo": mode,
    }

    raw = load_legacy_panel(xlsx_path)
    d1 = d1_diagnostics(raw)
    ledger.diagnostic(
        "D1 pib_percapita distintos por depto",
        d1["pib_pc_distintos_por_depto"]["media"],
        "5≈anual repetido / 14≈trimestral",
    )
    ledger.diagnostic(
        "D1 fracción crec_pib(t)==crec_pib(t-1)",
        d1["frac_crec_identico_lag"],
        "0.75 ⇒ dependiente sin variación trimestral",
    )

    panel, umbral = build_variables(raw, opts)
    panel = panel[panel["anio"].between(2017, 2021)].reset_index(drop=True)
    frac_cero = float((panel["crec_pib_pc"].round(6) == 0).mean())
    ledger.diagnostic("D1 fracción crec_pib_pc == 0", frac_cero, "0.75 ⇒ log-diff nulo dentro del año")

    # Sección 4: índice
    idx = build_pca_index(panel, VARS_PCA, ID_COLS, labels=LABELS_PCA)
    panel = panel.merge(
        idx.scores[ID_COLS + ["IIF", "IIF_PC1", "log_IIF", "IIF_std"]], on=ID_COLS, how="left"
    )
    ledger.check("KMO", idx.kmo if idx.kmo == idx.kmo else None, ledger.doc_otros["KMO"], tol=0.01)
    ledger.check(
        "Bartlett chi2",
        idx.bartlett if idx.bartlett == idx.bartlett else None,
        ledger.doc_otros["Bartlett_chi2"],
        tol=0.01,
    )
    ledger.check("Varianza acumulada 4 PC", float(idx.var_ac[3]), ledger.doc_otros["var_acum_4pc"], tol=0.01)
    ledger.check("Corr orientación IIF~cuentas", idx.corr_orient, ledger.doc_otros["corr_orient"], tol=0.03)

    # D2: sin internet
    idx_sn = build_pca_index(panel, VARS_PCA_SIN_INTERNET, ID_COLS, labels=LABELS_PCA)
    panel = panel.merge(
        idx_sn.scores[ID_COLS + ["IIF"]].rename(columns={"IIF": "IIF_sin_net"}), on=ID_COLS, how="left"
    )
    corr_sn = float(panel[["IIF", "IIF_sin_net"]].corr().iloc[0, 1])

    # D3: pesos 2017–2019
    base = panel[ID_COLS + VARS_PCA + ["anio"]].dropna().reset_index(drop=True)
    idx_oos = build_pca_index(
        base, VARS_PCA, ID_COLS, fit_mask=base["anio"].between(2017, 2019), labels=LABELS_PCA
    )
    panel = panel.merge(
        idx_oos.scores[ID_COLS + ["IIF"]].rename(columns={"IIF": "IIF_oos"}), on=ID_COLS, how="left"
    )
    corr_oos = float(panel[["IIF", "IIF_oos"]].corr().iloc[0, 1])

    # Sección 5–7
    pm = build_panel(panel)
    trace = sample_trace(pm)
    t6: dict[str, FitRow | None] = {
        "A1": fit_fe(pm, "IIF", "crec_pib_pc", dinamico=False, label="A1 FE-Est   | IIF"),
        "A2": fit_fe(pm, "IIF_lag1", "crec_pib_pc", dinamico=True, label="A2 FE-Dyn   | IIF_lag1"),
        "A3": fit_fe(
            pm,
            "IIF_lag1",
            "crec_pib_pc",
            dinamico=True,
            time_effects=True,
            label="A3 2way FE  | IIF_lag1  ← REFERENCIA",
        ),
        "A4": fit_fe(
            pm,
            "IIF",
            "crec_pib_pc",
            dinamico=False,
            time_effects=True,
            label="A4 2way FE  | IIF       ← FALTABA",
        ),
        "B1": fit_fe(pm, "IIF", "crec_pib", dinamico=False, label="B1 FE-Est   | IIF"),
        "B2": fit_fe(pm, "IIF_lag1", "crec_pib", dinamico=True, label="B2 FE-Dyn   | IIF_lag1"),
        "B3": fit_fe(pm, "IIF_PC1_lag1", "crec_pib", dinamico=True, label="B3 FE-Dyn   | IIF_PC1_lag1"),
        "B4": fit_fe(
            pm, "IIF_lag1", "crec_pib", dinamico=True, time_effects=True, label="B4 2way FE  | IIF_lag1"
        ),
    }
    for k, r in t6.items():
        doc = ledger.doc[k]
        ledger.check(f"Tabla6 {k} β", r.beta if r else None, doc["beta"], tol=0.02)
        ledger.check(f"Tabla6 {k} SE", r.se if r else None, doc["se"], tol=0.02)
        ledger.check(f"Tabla6 {k} N", r.N if r else None, doc["N"], tol=0.001)

    # Sección 8
    sub_h = pm.dropna(subset=["crec_pib", "IIF_lag1", "crec_pib_lag1"] + CTRL)
    rhs = "crec_pib_lag1 + IIF_lag1 + " + " + ".join(CTRL)
    hausman, m_fe = None, None
    try:
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            hausman, m_fe = dg.hausman_clustered(sub_h, rhs)
        ledger.check("Hausman chi2", hausman.chi2, ledger.doc_otros["Hausman_chi2"], tol=0.05)
    except Exception as exc:  # pragma: no cover
        say(f"Hausman: ERROR {exc}")
    mund = None
    try:
        mund = dg.mundlak(sub_h, "crec_pib_lag1 + IIF_lag1_within + IIF_lag1_mean + " + " + ".join(CTRL))
        ledger.check(
            "Mundlak IIF_mean",
            mund["beta_mean"],
            ledger.doc_otros["Mundlak_IIF_mean"],
            tol=0.05,
            nota="doc=4.11 | inicial=1.85 | correcciones=6.77",
        )
    except Exception as exc:  # pragma: no cover
        say(f"Mundlak: ERROR {exc}")
    cb, cw = dg.between_within_corr(sub_h)
    ledger.check("Corr between", cb, ledger.doc_otros["corr_between"], tol=0.10)
    ledger.check("Corr within", cw, ledger.doc_otros["corr_within"], tol=0.10)

    # Sección 9
    T = pm.index.get_level_values(1).nunique()
    nickell = {}
    for nombre, key, dvlag in [
        ("PIB agregado", "B2", "crec_pib_lag1"),
        ("PIB per cápita", "A2", "crec_pib_pc_lag1"),
    ]:
        r = t6[key]
        if r is not None and dvlag in r.model.params.index:
            nickell[nombre] = dg.nickell_bias(float(r.model.params[dvlag]), T)
    if "PIB agregado" in nickell:
        ledger.check(
            "rho Nickell (agregado)",
            nickell["PIB agregado"]["rho"],
            ledger.doc_otros["rho_nickell"],
            tol=0.03,
            nota="el documento usa el ρ del modelo AGREGADO",
        )

    # Sección 10
    rob: list[FitRow | None] = []
    pre = pm[pm["anio"].between(2017, 2019)]
    m_pre = fit_fe(pre, "IIF_lag1", "crec_pib", label="Pre-COVID | FE Entity")
    m_pre2 = fit_fe(pre, "IIF_lag1", "crec_pib", time_effects=True, label="Pre-COVID | two-way")
    rob += [m_pre, m_pre2]
    if m_pre is not None:
        ledger.check("Pre-COVID β", m_pre.beta, ledger.doc_otros["preCOVID_beta"], tol=0.30)
        ledger.check("Pre-COVID R²", m_pre.r2, ledger.doc_otros["preCOVID_r2"], tol=0.05)
    pesaran = ar1 = None
    if m_fe is not None:
        pesaran = dg.pesaran_cd(m_fe.resids)
        ledger.check("Pesaran CD", pesaran["CD"], ledger.doc_otros["Pesaran_CD"], tol=0.05)
        ar1 = dg.residual_ar1(m_fe.resids)
    m_dk = fit_fe(pm, "IIF_lag1", "crec_pib", cov="driscoll-kraay", label="FE Entity | DK SE")
    rob.append(m_dk)
    dk_vs = {"clustered": t6["B2"].se, "driscoll_kraay": m_dk.se} if (m_dk and t6["B2"]) else None
    q = pm["crec_pib"].quantile
    rob.append(
        fit_fe(pm[pm["crec_pib"].between(q(0.01), q(0.99))], "IIF_lag1", "crec_pib", label="Trimming 1%")
    )
    rob.append(
        fit_fe(
            pm.assign(crec_pib=pm["crec_pib"].clip(q(0.05), q(0.95))),
            "IIF_lag1",
            "crec_pib",
            label="Winsorización 5%",
        )
    )
    rob.append(fit_fe(pm, "IIF_lag2", "crec_pib_pc", label="IIF_lag2      | PIB pc"))
    rob.append(fit_fe(pm, "IIF_lag2", "crec_pib_pc", time_effects=True, label="IIF_lag2 2way | PIB pc"))
    rob.append(fit_fe(pm, "IIF_sin_net_lag1", "crec_pib_pc", label="IIF sin internet | PIB pc  (D2)"))
    rob.append(
        fit_fe(
            pm,
            "IIF_sin_net_lag1",
            "crec_pib_pc",
            time_effects=True,
            label="IIF sin internet 2way | PIB pc  (D2)",
        )
    )
    if pm["IIF_oos"].notna().any():
        rob.append(fit_fe(pm, "IIF_oos_lag1", "crec_pib_pc", label="IIF out-of-sample | PIB pc (D3)"))
        rob.append(
            fit_fe(
                pm,
                "IIF_oos_lag1",
                "crec_pib_pc",
                time_effects=True,
                label="IIF out-of-sample 2way | PIB pc (D3)",
            )
        )
    rob.append(
        fit_fe(pm.copy(), "IIF_lag1", "crec_pib", extra=["t_idx"], label="FE Entity + tendencia t_idx")
    )
    m_log = fit_fe(pm, "log_IIF_lag1", "crec_pib_pc", label="log(IIF)_lag1 | PIB pc")
    rob.append(m_log)
    if m_log is not None:
        ledger.check("β semi-elasticidad log", m_log.beta, ledger.doc_otros["beta_log"], tol=0.02)

    # Sección 11
    import warnings

    filas = []
    for cod, nombre in REGION_LABEL.items():
        dr = pm[pm["d_region"] == cod]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m_r = fit_fe(dr, "IIF_lag1", "crec_pib", label=nombre)
        if m_r is None:
            continue
        n_dep = (
            dr.dropna(subset=["crec_pib", "IIF_lag1", "crec_pib_lag1"] + CTRL)
            .index.get_level_values(0)
            .nunique()
        )
        filas.append(
            {
                "Region": nombre,
                "beta": m_r.beta,
                "se": m_r.se,
                "p": m_r.p,
                "N": int(m_r.N),
                "N_dep": int(n_dep),
            }
        )
    regional = pd.DataFrame(filas)

    # Sección 12
    desc = panel[VARS_DESC].describe(percentiles=[0.25, 0.5, 0.75]).T
    desc["N"] = panel[VARS_DESC].notna().sum()
    desc = desc[["N", "mean", "std", "min", "25%", "50%", "75%", "max"]]
    t2 = panel.groupby("anio").agg(
        N=("IIF", "size"),
        IIF_prom=("IIF", "mean"),
        crec_pib=("crec_pib", "mean"),
        crec_pib_pc=("crec_pib_pc", "mean"),
        log_IIF=("log_IIF", "mean"),
    )

    return LegacyResults(
        mode=mode,
        env=env,
        d1=d1,
        umbral_densidad=umbral,
        frac_cero_crec_pc=frac_cero,
        index=idx,
        index_sin_net=idx_sn,
        corr_iif_sin_net=corr_sn,
        index_oos=idx_oos,
        corr_iif_oos=corr_oos,
        trace=trace,
        tabla6=t6,
        hausman=hausman,
        mundlak=mund,
        corr_between=cb,
        corr_within=cw,
        nickell=nickell,
        robustez=rob,
        pesaran=pesaran,
        ar1=ar1,
        dk_vs_cluster=dk_vs,
        regional=regional,
        descriptivas=desc,
        tabla2=t2,
        ledger=ledger,
        lines=lines,
    )


def to_markdown(res: LegacyResults) -> str:
    L: list[str] = []
    w = L.append
    w("# Reproducción del notebook consolidado\n")
    w("## Entorno\n")
    for k, v in res.env.items():
        w(f"- {k}: `{v}`")
    w("\n## D1 — Estructura temporal\n")
    for col, d in res.d1["distintos_por_depto_anio"].items():
        w(f"- {col}: distintos por (depto, año) min={d['min']} max={d['max']} media={d['media']:.2f}")
    w(
        f"- pib_percapita distintos por departamento: media={res.d1['pib_pc_distintos_por_depto']['media']:.2f}"
    )
    w(f"- fracción crec_pib(t)==crec_pib(t-1): {res.d1['frac_crec_identico_lag']:.3f}")
    w(f"- fracción crec_pib_pc == 0: {res.frac_cero_crec_pc:.3f}")
    w("\n## Índice\n")
    i = res.index
    w(
        f"- KMO = {i.kmo:.4f} | Bartlett χ² = {i.bartlett:.2f} (p = {i.p_bartlett:.4f}) | componentes = {i.n_comp} | var. acum. = {i.var_ac[i.n_comp - 1]:.2f}%"
    )
    w(f"- pesos de componentes: {np.round(i.pesos, 4).tolist()} | corr(IIF, cuentas) = {i.corr_orient:.4f}")
    w(
        f"- corr(IIF, IIF sin internet) = {res.corr_iif_sin_net:.4f} | corr(IIF, IIF 2017–2019) = {res.corr_iif_oos:.4f}"
    )
    w("\nCargas:\n")
    w(i.loadings.round(4).to_markdown())
    w("\nPesos implícitos por variable (lo que el notebook nunca imprimió):\n")
    w(i.implied_weights.round(4).to_frame().to_markdown())
    w("\n## Tabla 6\n")
    w("```text")
    for r in res.tabla6.values():
        w(format_row(r))
    w("```")
    w("\n## Hausman, Mundlak, correlaciones\n")
    if res.hausman:
        w(
            f"- Hausman (NO válido con cov clusterizada): χ²({res.hausman.df}) = {res.hausman.chi2:.4f}, p = {res.hausman.p:.4f}"
        )
    if res.mundlak:
        w(
            f"- Mundlak: β_within = {res.mundlak['beta_within']:+.4f} (p={res.mundlak['p_within']:.4f}) | β_mean = {res.mundlak['beta_mean']:+.4f} (p={res.mundlak['p_mean']:.4f})"
        )
    w(f"- Corr between = {res.corr_between:+.4f} | Corr within = {res.corr_within:+.4f}")
    w("\n## Nickell\n")
    for k, v in res.nickell.items():
        w(
            f"- {k}: ρ̂ = {v['rho']:+.4f} | sesgo ≈ {v['sesgo']:+.4f} | ρ corregido ≈ {v['rho_corregido']:+.4f} | {v['pct_de_rho']:.1f}% de ρ̂"
        )
    w("\n## Robustez\n")
    w("```text")
    for r in res.robustez:
        w(format_row(r))
    w("```")
    if res.pesaran:
        w(
            f"- Pesaran CD = {res.pesaran['CD']:.4f}, p = {res.pesaran['p']:.4f} (N={res.pesaran['N']}, T medio={res.pesaran['T_medio']:.1f})"
        )
    if res.dk_vs_cluster:
        w(
            f"- SE clustered = {res.dk_vs_cluster['clustered']:.4f} → Driscoll-Kraay = {res.dk_vs_cluster['driscoll_kraay']:.4f}"
        )
    if res.ar1:
        w(f"- r(e_t, e_t-1) = {res.ar1['rho']:.4f}, p = {res.ar1['p']:.4f}")
    w("\n## Heterogeneidad regional\n")
    w(res.regional.round(4).to_markdown(index=False))
    w("\n## Descriptivas\n")
    w(res.descriptivas.round(4).to_markdown())
    w("\n")
    w(res.tabla2.round(4).to_markdown())
    w("\n## Verificación contra el documento\n")
    v = res.ledger_frame.copy()
    for c in ("obtenido", "documento"):
        v[c] = v[c].map(lambda x: "" if x is None or (isinstance(x, float) and x != x) else f"{x:,.4f}")
    w(v.to_markdown(index=False))
    w(f"\n**TOTAL DISCREPANCIAS: {res.ledger.n_discrepancias}**\n")
    return "\n".join(L) + "\n"
