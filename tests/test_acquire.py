"""Pruebas de adquisición con HTTP simulado (`responses`): paginación, conteo, idempotencia, puerta de tamaño,
vintages por Last-Modified, paginación ArcGIS y manifiesto. Ninguna toca la red."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import responses

from iif.acquire import dane, mgn, soda
from iif.acquire.manifest import read_records, verify_manifest
from iif.acquire.sources import get_source, load_sources

DS = "test-0001"
META_URL = f"{soda.BASE}/api/views/{DS}.json"
RES_URL = f"{soda.BASE}/resource/{DS}.json"


def _rows(n: int, start: int = 0) -> list[dict]:
    return [
        {
            "fecha_corte": f"{2018 + (i % 2)}-03-31T00:00:00.000",
            "nombre": f"m{i}",
            "nro_cuentas": str(i * 10),
            "saldo": f"{i},5",
        }
        for i in range(start, start + n)
    ]


def _mock_soda(
    rsps: responses.RequestsMock, rows: list[dict], *, updated: int = 1_700_000_000, page: int = 2
):
    rsps.get(
        META_URL,
        json={"name": "t", "rowsUpdatedAt": updated, "license": {"name": "CC-BY-SA-4.0"}, "columns": []},
    )
    rsps.get(
        RES_URL,
        json=[{"n": str(len(rows))}],
        match=[responses.matchers.query_param_matcher({"$select": "count(*) as n"})],
    )
    for off in range(0, len(rows) + page, page):
        chunk = rows[off : off + page]
        rsps.get(
            RES_URL,
            json=chunk,
            match=[
                responses.matchers.query_param_matcher(
                    {"$limit": str(page), "$offset": str(off), "$order": ":id"}
                )
            ],
        )


def _source(tmp_path: Path, **over) -> dict:
    return {
        "id": "test-soda",
        "dataset": DS,
        "partition_col": "fecha_corte",
        "date_cols": ["fecha_corte"],
        "numeric_regex": "^(nro|saldo)",
        "license": "CC-BY-SA-4.0",
        "max_file_mb": 45,
        "page_size": 2,
        **over,
    }


@responses.activate
def test_soda_paging_partitions_and_manifest(tmp_path: Path):
    rows = _rows(5)
    _mock_soda(responses, rows)
    man = tmp_path / "manifest.jsonl"
    recs = soda.fetch_soda(_source(tmp_path), out_dir=tmp_path / "raw", manifest=man)
    assert sorted(Path(r.path).parent.name for r in recs) == ["anio=2018", "anio=2019"]
    assert sum(r.row_count for r in recs) == 5
    df = pd.concat(pd.read_parquet(r.path) for r in recs)
    assert df["nro_cuentas"].dtype.kind in "if"
    assert set(df["saldo"]) == {i + 0.5 for i in range(5)}, "decimales con coma → float"
    assert str(df["fecha_corte"].dtype).startswith("datetime64")
    assert df["pull_id"].nunique() == 1 and df["pull_id"].iloc[0].startswith("test-soda__")
    saved = read_records(man)
    assert len(saved) == 2 and all(r.sha256 and r.source_updated_at == "2023-11-14T22:13:20Z" for r in saved)
    assert verify_manifest(man, root=tmp_path) == []


@responses.activate
def test_soda_skips_when_source_unchanged_and_force_redownloads(tmp_path: Path):
    rows = _rows(3)
    _mock_soda(responses, rows)
    man = tmp_path / "manifest.jsonl"
    first = soda.fetch_soda(_source(tmp_path), out_dir=tmp_path / "raw", manifest=man)
    assert first
    again = soda.fetch_soda(_source(tmp_path), out_dir=tmp_path / "raw", manifest=man)
    assert again == [], "mismo rowsUpdatedAt → no se vuelve a descargar"
    forced = soda.fetch_soda(_source(tmp_path), out_dir=tmp_path / "raw", manifest=man, force=True)
    assert len(forced) == len(first)
    assert len(read_records(man)) == 2 * len(first)


@responses.activate
def test_soda_count_mismatch_raises(tmp_path: Path):
    rows = _rows(4)
    _mock_soda(responses, rows)
    responses.replace(
        responses.GET,
        RES_URL,
        json=[{"n": "99"}],
        match=[responses.matchers.query_param_matcher({"$select": "count(*) as n"})],
    )
    with pytest.raises(RuntimeError, match="la fuente dice 99"):
        soda.fetch_soda(_source(tmp_path), out_dir=tmp_path / "raw", manifest=tmp_path / "m.jsonl")


@responses.activate
def test_soda_size_gate_moves_partition_out_of_git(tmp_path: Path):
    rows = _rows(6)
    _mock_soda(responses, rows)
    man = tmp_path / "manifest.jsonl"
    out = tmp_path / "raw"
    with pytest.raises(soda.SizeGateError, match="superan"):
        soda.fetch_soda(_source(tmp_path, max_file_mb=1e-6), out_dir=out, manifest=man)
    recs = read_records(man)
    assert recs and all(Path(r.path).is_relative_to(out / "_large") for r in recs)
    assert all(Path(r.path).exists() for r in recs) and not list((out / "test_soda").rglob("*.parquet"))
    assert all("ADR-003" in r.notes for r in recs)
    assert verify_manifest(man, root=tmp_path) == []


def test_type_frame_comma_decimals_and_regex():
    df = pd.DataFrame(
        {
            "saldo_total": ["1,5", "2"],
            "nro_x": ["3", "x"],
            "nombre": ["a", "b"],
            "f": ["2019-03-31", "2019-06-30"],
        }
    )
    out = soda.type_frame(df, numeric_regex="^(saldo|nro)", numeric_cols=None, date_cols=["f"])
    assert out["saldo_total"].tolist() == [1.5, 2.0]
    assert out["nro_x"].isna().tolist() == [False, True]
    assert out["nombre"].tolist() == ["a", "b"]
    assert str(out["f"].dtype).startswith("datetime64")


@responses.activate
def test_dane_last_modified_in_filename_and_skip(tmp_path: Path):
    url = "https://www.dane.gov.co/files/x/anex-PIB-2025pr.xlsx"
    lm = "Fri, 03 Jul 2026 14:02:11 GMT"
    responses.head(url, headers={"Last-Modified": lm})
    responses.get(url, body=b"PK\x03\x04fake", headers={"Last-Modified": lm})
    src = {"id": "dane-x", "url": url, "license": "DANE"}
    man = tmp_path / "manifest.jsonl"
    rec = dane.fetch_file(src, out_dir=tmp_path / "dane", manifest=man)
    assert rec is not None and Path(rec.path).name == "anex-PIB-2025pr__lm20260703.xlsx"
    assert rec.source_updated_at == "2026-07-03T14:02:11Z" and rec.bytes == 8
    assert dane.fetch_file(src, out_dir=tmp_path / "dane", manifest=man) is None
    assert dane.fetch_file(src, out_dir=tmp_path / "dane", manifest=man, force=True) is not None
    assert len(read_records(man)) == 2


@responses.activate
def test_dane_without_last_modified_uses_pull_date(tmp_path: Path):
    url = "https://www.dane.gov.co/files/x/serie.xlsx"
    responses.head(url, status=405)
    responses.get(url, body=b"data")
    rec = dane.fetch_file({"id": "dane-y", "url": url}, out_dir=tmp_path, manifest=tmp_path / "m.jsonl")
    assert rec.source_updated_at is None and "__lm" in Path(rec.path).name


def _feature(i: int) -> dict:
    return {
        "type": "Feature",
        "properties": {"DPTO_CCDGO": f"{i:02d}", "DPTO_CNMBR": f"D{i}"},
        "geometry": {"type": "Point", "coordinates": [-74.0 + i, 4.0]},
    }


@responses.activate
def test_mgn_pages_until_transfer_limit_clears(tmp_path: Path):
    url = f"{mgn.SERVICE}/319/query"
    responses.get(
        url,
        json={
            "type": "FeatureCollection",
            "features": [_feature(i) for i in range(2)],
            "exceededTransferLimit": True,
        },
        match=[responses.matchers.query_param_matcher({"resultOffset": "0"}, strict_match=False)],
    )
    responses.get(
        url,
        json={
            "type": "FeatureCollection",
            "features": [_feature(2), _feature(3)],
            "exceededTransferLimit": False,
        },
        match=[responses.matchers.query_param_matcher({"resultOffset": "2"}, strict_match=False)],
    )
    src = {"id": "mgn-departamentos", "layer": 319, "precision": 5}
    man = tmp_path / "m.jsonl"
    out = tmp_path / "dep.geojson"
    rec = mgn.fetch_layer(src, out_path=out, manifest=man, page_size=2)
    assert rec.row_count == 4 and len(responses.calls) == 2
    attrs = mgn.geojson_attributes(out)
    assert attrs["DPTO_CCDGO"].tolist() == ["00", "01", "02", "03"]
    assert mgn.fetch_layer(src, out_path=out, manifest=man, page_size=2) is None, "mismo sha256 → se salta"
    assert mgn.fetch_layer(src, out_path=out, manifest=man, page_size=2, force=True) is not None


@responses.activate
def test_mgn_service_error_raises(tmp_path: Path):
    responses.get(f"{mgn.SERVICE}/317/query", json={"error": {"code": 400, "message": "Invalid"}})
    with pytest.raises(RuntimeError, match="devolvió error"):
        mgn.fetch_layer(
            {"id": "mgn-municipios", "layer": 317},
            out_path=tmp_path / "m.geojson",
            manifest=tmp_path / "m.jsonl",
        )


def test_manifest_verify_detects_missing_and_modified(tmp_path: Path):
    from iif.acquire.manifest import PullRecord, append_record, sha256_of

    f = tmp_path / "a.bin"
    f.write_bytes(b"abc")
    man = tmp_path / "m.jsonl"
    append_record(
        PullRecord(pull_id="p1", source_id="s", dataset_id=None, url="u", sha256=sha256_of(f), path="a.bin"),
        man,
    )
    append_record(
        PullRecord(pull_id="p2", source_id="s2", dataset_id=None, url="u", sha256="00", path="missing.bin"),
        man,
    )
    assert verify_manifest(man, root=tmp_path) == ["falta missing.bin (p2)"]
    f.write_bytes(b"abcd")
    probs = verify_manifest(man, root=tmp_path)
    assert probs == ["sha256 distinto en a.bin (p1)", "falta missing.bin (p2)"]


def test_sources_yaml_is_consistent():
    sources = load_sources()
    assert len(sources) >= 19
    kinds = {"soda", "http", "arcgis"}
    for sid, s in sources.items():
        assert s["kind"] in kinds, sid
        assert "descripcion" in s and "license" in s, sid
        if s["kind"] == "soda":
            assert "dataset" in s and "partition_col" in s, sid
        elif s["kind"] == "http":
            assert s["url"].startswith("https://"), sid
        else:
            assert isinstance(s["layer"], int), sid
    assert get_source("sfc-kx2f-xjdq")["dataset"] == "kx2f-xjdq"
    with pytest.raises(KeyError):
        get_source("no-existe")
    assert json.dumps(sources)  # serializable (lo consume el manifiesto)


@responses.activate
def test_soda_page_missing_columns_keeps_types(tmp_path: Path):
    """Socrata omite las claves nulas: una página puede no traer una columna. El tipo debe sobrevivir."""
    rows = _rows(4)
    for r in rows[2:]:
        r.pop("saldo")
        r.pop("fecha_corte")
    _mock_soda(responses, rows)
    recs = soda.fetch_soda(_source(tmp_path), out_dir=tmp_path / "raw", manifest=tmp_path / "m.jsonl")
    df = pd.concat(pd.read_parquet(r.path) for r in recs)
    assert {Path(r.path).parent.name for r in recs} == {"anio=2018", "anio=2019", "anio=sin_fecha"}
    assert df["saldo"].dtype.kind == "f" and df["saldo"].isna().sum() == 2
    assert str(df["fecha_corte"].dtype).startswith("datetime64") and df["fecha_corte"].isna().sum() == 2


def test_typing_from_metadata_keeps_codes_as_text():
    meta = {
        "types": {
            "codigo_municipio": "number",
            "saldo": "number",
            "fecha_corte": "calendar_date",
            "nombre": "text",
        }
    }
    src = {
        "code_cols": ["codigo_municipio"],
        "numeric_cols": ["extra", "codigo_municipio"],
        "date_cols": ["otra_fecha"],
    }
    t = soda.typing_from_metadata(src, meta)
    assert t["numeric_cols"] == ["extra", "saldo"]
    assert t["date_cols"] == ["fecha_corte", "otra_fecha"]
    assert t["code_cols"] == ["codigo_municipio"]
    df = pd.DataFrame(
        {"codigo_municipio": ["05001"], "saldo": ["1,5"], "fecha_corte": ["2019-03-31T00:00:00.000"]}
    )
    out = soda.type_frame(df, **t)
    assert out["codigo_municipio"].tolist() == ["05001"] and out["saldo"].tolist() == [1.5]


@responses.activate
def test_soda_redownload_replaces_old_partitions(tmp_path: Path):
    rows = _rows(4)
    _mock_soda(responses, rows, updated=1)
    man = tmp_path / "m.jsonl"
    out = tmp_path / "raw"
    soda.fetch_soda(_source(tmp_path), out_dir=out, manifest=man)
    assert sorted(p.name for p in (out / "test_soda").iterdir()) == ["anio=2018", "anio=2019"]
    responses.reset()
    only_2018 = [r for r in rows if r["fecha_corte"].startswith("2018")]
    _mock_soda(responses, only_2018, updated=2)
    soda.fetch_soda(_source(tmp_path), out_dir=out, manifest=man)
    assert sorted(p.name for p in (out / "test_soda").iterdir()) == ["anio=2018"], (
        "la partición vieja se borra"
    )
    assert verify_manifest(man, root=tmp_path) == [], "solo se verifica la última descarga de cada fuente"


@responses.activate
def test_mgn_null_geometry_is_an_error(tmp_path: Path):
    feats = [{"type": "Feature", "properties": {"DPTO_CCDGO": "05"}, "geometry": None}]
    responses.get(f"{mgn.SERVICE}/319/query", json={"type": "FeatureCollection", "features": feats})
    with pytest.raises(RuntimeError, match="sin geometría"):
        mgn.fetch_layer(
            {"id": "mgn-departamentos", "layer": 319},
            out_path=tmp_path / "d.geojson",
            manifest=tmp_path / "m.jsonl",
        )


@responses.activate
def test_soda_unknown_partition_column_raises(tmp_path: Path):
    _mock_soda(responses, _rows(2))
    with pytest.raises(ValueError, match="columna de partición"):
        soda.fetch_soda(
            _source(tmp_path, partition_col="fecha_de_corte"), out_dir=tmp_path, manifest=tmp_path / "m.jsonl"
        )
