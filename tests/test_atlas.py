"""Exportación del atlas: geometría válida, presupuesto y forma de las series (ADR-005)."""

from __future__ import annotations

import json
import math

import pytest

from iif import config
from iif.export.atlas import build_series, load_contract

DATA = config.REPO_ROOT / "atlas" / "data"
pytestmark = pytest.mark.skipif(
    not (DATA / "atlas_meta.json").exists(), reason="sin atlas/data; corre `make atlas`"
)


def _anillos(topo: dict):
    """Reconstruye los anillos exteriores en grados desde los arcos delta del TopoJSON."""
    tr = topo["transform"]
    sx, sy = tr["scale"]
    dx, dy = tr["translate"]
    arcos = []
    for arco in topo["arcs"]:
        x = y = 0.0
        pts = []
        for ddx, ddy in arco:
            x += ddx
            y += ddy
            pts.append((x * sx + dx, y * sy + dy))
        arcos.append(pts)

    def unir(indices):
        pts: list[tuple[float, float]] = []
        for i in indices:
            seg = arcos[i] if i >= 0 else arcos[~i][::-1]
            pts.extend(seg if not pts else seg[1:])
        return pts

    for geom in next(iter(topo["objects"].values()))["geometries"]:
        polis = geom["arcs"] if geom["type"] == "MultiPolygon" else [geom["arcs"]]
        for poli in polis:
            yield geom["properties"]["id"], unir(poli[0])


def _area(pts) -> float:
    return sum(pts[i][0] * pts[i + 1][1] - pts[i + 1][0] * pts[i][1] for i in range(len(pts) - 1)) / 2


@pytest.mark.parametrize("nivel,n_esperado", [("departamentos", 33), ("municipios", 1121)])
def test_geometria_tiene_todas_las_unidades_y_el_giro_correcto(nivel, n_esperado):
    """B-039: TopoJSON y d3 esperan el anillo exterior en sentido horario (área con signo negativa).

    Con el giro de RFC 7946, d3 lee cada anillo como el complemento del polígono y el mapa se vuelve un
    rectángulo de color. Un anillo de área cero produce lo mismo.
    """
    topo = json.loads((DATA / f"geo_{nivel}.json").read_text(encoding="utf-8"))
    geoms = next(iter(topo["objects"].values()))["geometries"]
    assert len(geoms) == n_esperado
    areas = [(uid, _area(pts)) for uid, pts in _anillos(topo)]
    invertidos = [(uid, a) for uid, a in areas if a >= 0]
    assert not invertidos, f"anillos con giro de RFC 7946 o degenerados: {invertidos[:5]}"


def test_la_superficie_total_es_la_de_colombia():
    """S-014: la suma de las áreas debe dar el área real del país, no cualquier número.

    Colombia mide 1.142.000 km² sobre una esfera de 510,1 millones: 0,0281 estereorradianes. Antes de
    corregir el giro, la suma daba 590. Es la prueba que detecta el fallo sin mirar el mapa.
    """
    topo = json.loads((DATA / "geo_departamentos.json").read_text(encoding="utf-8"))
    # Área plana en grados² convertida a estereorradianes con el coseno de la latitud media (5°N).
    grados2 = sum(abs(_area(pts)) for _, pts in _anillos(topo))
    estereorradianes = grados2 * (math.pi / 180) ** 2 * math.cos(math.radians(5))
    assert 0.024 < estereorradianes < 0.032, (
        f"la superficie da {estereorradianes:.5f} sr, Colombia mide 0,0281"
    )


def test_el_atlas_cabe_en_su_presupuesto():
    contrato = load_contract()
    total = sum(p.stat().st_size for p in DATA.glob("*.json")) / 1e6
    assert total <= float(contrato["presupuesto_mb"]), f"{total:.2f} MB"


def test_las_series_declaran_lo_que_traen():
    meta = json.loads((DATA / "atlas_meta.json").read_text(encoding="utf-8"))
    for nivel, indicadores in meta["indicadores"].items():
        datos = json.loads((DATA / f"series_{nivel}.json").read_text(encoding="utf-8"))
        assert set(datos["series"]) == {i["id"] for i in indicadores}
        n_u, n_a = len(datos["ids"]), len(datos["anios"])
        assert len(datos["nombres"]) == n_u
        for ind, matriz in datos["series"].items():
            assert len(matriz) == n_a, ind
            assert all(len(fila) == n_u for fila in matriz), ind
    assert meta["islas_descartadas"], "el descarte de islas debe publicarse, no ser silencioso"


def test_los_acompanantes_conservan_su_tipo():
    """Un booleano llega como booleano y un codigo DIVIPOLA como texto.

    `str(True)` produce `"True"`, que en el navegador no es ni `true` ni `"true"`: la comparacion falla en
    silencio y la capa que dependa de ella deja de dibujarse sin que nada avise (B-040).
    """
    datos = json.loads((DATA / "series_municipio.json").read_text(encoding="utf-8"))
    assert all(isinstance(v, bool) for v in datos["es_capital"])
    assert sum(datos["es_capital"]) == 33, "una capital por departamento"
    assert all(v is None or isinstance(v, str) for v in datos["dpto_ccdgo"])
    assert all(len(v) == 2 for v in datos["dpto_ccdgo"] if v), "el codigo de departamento lleva su cero"


def test_build_series_deja_nulo_lo_no_observado():
    import pandas as pd

    df = pd.DataFrame(
        {
            "dpto_ccdgo": ["05", "05", "08"],
            "departamento": ["Antioquia", "Antioquia", "Atlántico"],
            "region": ["Andina", "Andina", "Caribe"],
            "anio": [2018, 2019, 2018],
            "iif_compuesto": [1.234567, None, -0.5],
        }
    )
    datos = build_series("departamento", [{"id": "iif_compuesto", "decimales": 3}], df)
    assert datos["ids"] == ["05", "08"] and datos["anios"] == [2018, 2019]
    assert datos["series"]["iif_compuesto"] == [[1.235, -0.5], [None, None]]
