"""Diccionario de las 102 columnas del panel legado: fuente estimada, frecuencia real y uso."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from iif.legacy.constants import RENAME_MAP, USED_RAW_COLUMNS

CALENDAR = {"Año", "Mes", "short quarter", "quarter", "Meses Nombre", "Fecha", "Depto Base"}


def _fuente(col: str) -> str:
    c = col.upper()
    if col in CALENDAR:
        return "clave"
    if any(
        k in c
        for k in (
            "CORRESPONSAL",
            "DEPOSITO",
            "GIRO",
            "PAGO",
            "RETIRO",
            "TRANSFER",
            "NRO TOTAL",
            "MONTO TOTAL",
        )
    ):
        return "SFC / Banca de las Oportunidades (transaccional y corresponsales)"
    if any(k in c for k in ("CTA AHORRO", "CREDITO", "MICROCREDITO")):
        return "SFC / Banca de las Oportunidades (productos)"
    if "INTERNET" in c or c.endswith(" %") and any(k in c for k in ("FIJO", "MOVIL")):
        return "MinTIC (internet)"
    if "EDUCACI" in c:
        return "DANE GEIH (educación)"
    if "IPC" in c:
        return "DANE IPC por ciudad"
    if "EMPLEO" in c:
        return "DANE GEIH (empleo)"
    if "PIB" in c:
        return "DANE cuentas departamentales"
    if "POBLACION" in c or "DENSIDAD" in c:
        return "DANE proyecciones de población"
    if "SUPERFICIE" in c:
        return "IGAC / DANE"
    if col in ("Llave", "Capital"):
        return "derivada / catálogo"
    return "sin clasificar"


def _derivada(col: str) -> bool:
    c = col.upper()
    return (
        "TOTAL" in c or col in ("Llave", "Densidad Poblacional") or c.endswith(" %") and "INTERNET" not in c
    )


def build_dictionary(xlsx_or_parquet: Path) -> pd.DataFrame:
    df = (
        pd.read_parquet(xlsx_or_parquet)
        if xlsx_or_parquet.suffix == ".parquet"
        else pd.read_excel(xlsx_or_parquet)
    )
    df.columns = df.columns.str.strip()
    rows = []
    for i, col in enumerate(df.columns):
        s = df[col]
        n_unique = int(s.nunique(dropna=False))
        if col in CALENDAR:
            frecuencia = "clave"
        elif n_unique == 1:
            frecuencia = "muerta (1 valor)"
        elif n_unique == 33:
            frecuencia = "estática (33 valores)"
        else:
            max_por_anio = int(df.groupby(["Depto Base", "Año"])[col].nunique().max())
            frecuencia = "trimestral" if max_por_anio > 1 else "anual repetida"
        rows.append(
            {
                "indice": i,
                "columna": col,
                "nombre_notebook": RENAME_MAP.get(col, ""),
                "dtype": str(s.dtype),
                "n_unicos": n_unique,
                "min": s.min() if pd.api.types.is_numeric_dtype(s) else "",
                "max": s.max() if pd.api.types.is_numeric_dtype(s) else "",
                "frecuencia_real": frecuencia,
                "fuente_estimada": _fuente(col),
                "derivada": _derivada(col),
                "usada_por_notebook": col in USED_RAW_COLUMNS,
            }
        )
    return pd.DataFrame(rows)
