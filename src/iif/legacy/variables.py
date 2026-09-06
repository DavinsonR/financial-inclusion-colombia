"""Construcción de variables del notebook (sección 3) con las correcciones como opciones."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from iif.legacy.constants import COL_TIEMPO, REGION_MAP


@dataclass(frozen=True)
class VariableOptions:
    deflator: str = "first_row"  # "first_row" (bug del notebook: IPC de Amazonas) | "by_department"
    internet_zero_is_missing: bool = False
    profundidad_flows: str = "quarterly"  # "quarterly" (flujo trimestral / PIB anual) | "annual_rate" (x4)
    urban_threshold_over: str = "rows"  # "rows" (cuantil sobre 462 filas) | "departments" (sobre 33)

    @classmethod
    def for_mode(cls, mode: str) -> VariableOptions:
        if mode == "notebook":
            return cls()
        if mode == "corrected":
            return cls(
                deflator="by_department",
                internet_zero_is_missing=True,
                profundidad_flows="annual_rate",
                urban_threshold_over="departments",
            )
        raise ValueError(f"modo desconocido: {mode}")


def _ipc_index_first_row(df: pd.DataFrame) -> pd.Series:
    ipc = df[["anio", "IPC_pct"]].drop_duplicates("anio").sort_values("anio").reset_index(drop=True)
    base = pd.DataFrame({"anio": [2016], "IPC_pct": [0.0]})
    ipc = (
        pd.concat([base, ipc])
        .drop_duplicates("anio", keep="first")
        .sort_values("anio")
        .reset_index(drop=True)
    )
    ipc["ipc_index"] = 100 * (1 + ipc["IPC_pct"] / 100).cumprod()
    return df["anio"].map(ipc.set_index("anio")["ipc_index"])


def _ipc_index_by_department(df: pd.DataFrame) -> pd.Series:
    ipc = (
        df[["departamento", "anio", "IPC_pct"]]
        .drop_duplicates(["departamento", "anio"])
        .sort_values(["departamento", "anio"])
    )
    ipc["ipc_index"] = ipc.groupby("departamento")["IPC_pct"].transform(
        lambda s: 100 * (1 + s / 100).cumprod()
    )
    key = list(zip(df["departamento"], df["anio"], strict=False))
    lookup = ipc.set_index(["departamento", "anio"])["ipc_index"]
    return pd.Series([lookup.get(k, np.nan) for k in key], index=df.index)


def build_variables(df: pd.DataFrame, opts: VariableOptions | None = None) -> tuple[pd.DataFrame, float]:
    opts = opts or VariableOptions()
    df = df.copy()
    df["ipc_index"] = (
        _ipc_index_first_row(df) if opts.deflator == "first_row" else _ipc_index_by_department(df)
    )
    df = df.sort_values(["departamento", COL_TIEMPO]).reset_index(drop=True)

    if opts.internet_zero_is_missing:
        df.loc[df["internet_pct"] == 0, "internet_pct"] = np.nan

    pob = df["poblacion"]
    p_ = df["ipc_index"] / 100
    df["pib_pc_real"] = df["pib_percapita"] / p_
    df["pib_nominal_aprox"] = df["pib_percapita"] * pob
    df["crec_pib"] = df["pib_crecimiento"]
    df["crec_pib_pc"] = df.groupby("departamento")["pib_pc_real"].transform(
        lambda x: (np.log(x) - np.log(x.shift(1))) * 100
    )

    df["fintech_nro_pc"] = (df["nro_total"] / pob) * 1_000
    df["log_fintech_pc"] = np.log(df["fintech_nro_pc"].clip(lower=1e-9))

    flow_scale = 4.0 if opts.profundidad_flows == "annual_rate" else 1.0
    df["d_acc_corresp"] = (df["nro_corresp_activos"] / pob) * 10_000
    df["d_acc_cta_ah"] = (df["nro_total_cta_ah"] / pob) * 1_000
    df["d_acc_internet"] = df["internet_pct"]
    df["d_uso_pagos_pc"] = (df["nro_pagos"] / pob) * 1_000
    df["d_uso_transf_pc"] = (df["nro_transf"] / pob) * 1_000
    df["d_uso_depositos_pc"] = (df["nro_depositos"] / pob) * 1_000
    df["d_pro_micro"] = flow_scale * df["monto_total_micro"] / df["pib_nominal_aprox"]
    df["d_pro_cred_cons"] = flow_scale * df["monto_total_cred_cons"] / df["pib_nominal_aprox"]
    df["d_pro_cred_viv"] = flow_scale * df["monto_total_cred_viv"] / df["pib_nominal_aprox"]

    df["densidad"] = df["Densidad_Poblacional"]
    df["educacion"] = df["educacion_anios"]
    df["informalidad"] = (df["Empleo_Informal"] / (df["Empleo_Formal"] + df["Empleo_Informal"])) * 100
    df["d_covid"] = (df["anio"] == 2020).astype(int)

    med = df.groupby("departamento")["densidad"].median()
    df["densidad_mediana"] = df["departamento"].map(med)
    umbral = (
        float(df["densidad_mediana"].quantile(0.75))
        if opts.urban_threshold_over == "rows"
        else float(med.quantile(0.75))
    )
    df["urbano"] = (df["densidad_mediana"] > umbral).astype(int)
    df["zona"] = df["urbano"].map({1: "Urbano", 0: "Rural"})
    df["d_region"] = df["departamento"].str.strip().str.lower().map(REGION_MAP)
    df["t_idx"] = df.groupby("departamento").cumcount() + 1
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    return df, umbral


def d1_diagnostics(raw: pd.DataFrame) -> dict:
    """D1: ¿el PIB y los controles son anuales repetidos en los trimestres?"""
    out: dict = {"distintos_por_depto_anio": {}}
    for col in [
        "pib_percapita",
        "pib_crecimiento",
        "IPC_pct",
        "internet_pct",
        "educacion_anios",
        "Empleo_Informal",
    ]:
        if col in raw.columns:
            nu = raw.groupby(["departamento", "anio"])[col].nunique()
            out["distintos_por_depto_anio"][col] = {
                "min": int(nu.min()),
                "max": int(nu.max()),
                "media": float(nu.mean()),
            }
    nu_dep = raw.groupby("departamento")["pib_percapita"].nunique()
    out["pib_pc_distintos_por_depto"] = {
        "min": int(nu_dep.min()),
        "max": int(nu_dep.max()),
        "media": float(nu_dep.mean()),
    }
    tmp = raw.sort_values(["departamento", COL_TIEMPO]).copy()
    tmp["g_lag"] = tmp.groupby("departamento")["pib_crecimiento"].shift(1)
    out["frac_crec_identico_lag"] = float((tmp["pib_crecimiento"] == tmp["g_lag"]).mean())
    return out
