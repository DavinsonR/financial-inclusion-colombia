"""Libro de verificación: cada cifra obtenida frente a la que publica el documento de la tesis."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from iif.config import CONFIG_DIR, load_yaml


@dataclass
class Ledger:
    doc: dict
    doc_otros: dict
    rows: list[dict] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: Path | None = None) -> Ledger:
        cfg = load_yaml(path or CONFIG_DIR / "tesis_documento.yaml")
        return cls(doc=cfg["tabla6"], doc_otros=cfg["otros"])

    def check(self, nombre: str, obtenido, documento, tol: float = 0.02, nota: str = "") -> str:
        if documento is None:
            estado = "SIN DATO EN DOC"
        elif obtenido is None or (isinstance(obtenido, float) and obtenido != obtenido):
            estado = "NO ESTIMADO"
        else:
            rel = abs(obtenido - documento) / max(abs(documento), 1e-9)
            estado = "OK" if rel <= tol else "DISCREPA"
        self.rows.append(
            {"item": nombre, "obtenido": obtenido, "documento": documento, "estado": estado, "nota": nota}
        )
        return estado

    def diagnostic(self, nombre: str, obtenido, nota: str = "") -> None:
        self.rows.append(
            {"item": nombre, "obtenido": obtenido, "documento": None, "estado": "DIAGNÓSTICO", "nota": nota}
        )

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows, columns=["item", "obtenido", "documento", "estado", "nota"])

    @property
    def n_discrepancias(self) -> int:
        return sum(1 for r in self.rows if r["estado"] == "DISCREPA")
