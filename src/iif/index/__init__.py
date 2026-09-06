"""Índice de inclusión financiera en dos etapas (ADR-015).

Un componente principal por dimensión sobre variables normalizadas y estandarizadas da tres subíndices
(acceso, uso, profundidad); el compuesto los promedia con el mismo peso. Los parámetros se estiman en la
ventana de calibración y se congelan en `config/index.yaml`: a partir de ahí el índice se reproduce
exactamente, y añadir un año no cambia los años anteriores.
"""

from iif.index.build import (
    IndexResult,
    build_index,
    load_contract,
    normalize_panel,
    pesos_implicitos,
)

__all__ = ["IndexResult", "build_index", "load_contract", "normalize_panel", "pesos_implicitos"]
