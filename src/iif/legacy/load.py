from __future__ import annotations

from pathlib import Path

import pandas as pd

from iif.legacy.constants import RENAME_MAP


def load_legacy_panel(path: Path) -> pd.DataFrame:
    """Lee el panel congelado (xlsx o parquet), recorta cabeceras y aplica el rename del notebook."""
    df = pd.read_parquet(path) if Path(path).suffix == ".parquet" else pd.read_excel(path)
    df.columns = df.columns.str.strip()
    df = df.rename(columns=RENAME_MAP)
    df["Fecha"] = pd.to_datetime(df["Fecha"])
    return df
