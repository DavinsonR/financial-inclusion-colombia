"""CLI: los errores de uso se detectan antes de tocar la red o los datos."""

from __future__ import annotations

from typer.testing import CliRunner

from iif import config
from iif.cli import app

runner = CliRunner()


def test_acquire_unknown_source_is_a_usage_error():
    res = runner.invoke(app, ["acquire", "no-existe"])
    assert res.exit_code == 2 and "fuente desconocida" in res.output


def test_crosswalk_unknown_fuente_is_a_usage_error():
    res = runner.invoke(app, ["crosswalk", "geo-report", "--fuente", "xyz"])
    assert res.exit_code == 2


def test_duckdb_path_follows_the_same_variable_as_dbt(monkeypatch, tmp_path):
    monkeypatch.delenv("IIF_DUCKDB_PATH", raising=False)
    assert config._duckdb_path() == config.REPO_ROOT / "db" / "iif.duckdb"
    monkeypatch.setenv("IIF_DUCKDB_PATH", str(tmp_path / "w.duckdb"))
    assert config._duckdb_path() == tmp_path / "w.duckdb"
    monkeypatch.setenv("IIF_DUCKDB_PATH", "db/otro.duckdb")
    assert config._duckdb_path() == config.REPO_ROOT / "db" / "otro.duckdb"
