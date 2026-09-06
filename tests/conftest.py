from __future__ import annotations

import pytest

from iif import config


@pytest.fixture(scope="session")
def legacy_results():
    """Corre el pipeline legado una sola vez por sesión de pruebas (≈7 s)."""
    from iif.legacy.pipeline import run_legacy_pipeline

    if not config.LEGACY_PARQUET.exists():
        pytest.skip("falta data/legacy/panel_fintech_colombia_trimestral.parquet")
    return run_legacy_pipeline(config.LEGACY_PARQUET, mode="notebook")


def approx_rel(value, expected, rel=1e-3):
    return value == pytest.approx(expected, rel=rel)
