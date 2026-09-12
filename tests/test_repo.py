"""Invariantes del repositorio: reglas de CLAUDE.md que una prueba puede vigilar (R-12, R-15, CI válido)."""

from __future__ import annotations

import glob
import re

import yaml

from iif import config

ROOT = config.REPO_ROOT
ANCLAS = ["status", "abstract", "data", "method", "main-result", "diagnostics", "que-hay-y-que-falta"]


def test_readme_keeps_the_seven_anchors():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    ids = set(re.findall(r'<a id="([^"]+)"', readme))
    assert set(ANCLAS) <= ids, sorted(set(ANCLAS) - ids)


def test_claude_md_fits_in_forty_lines():
    lines = (ROOT / "CLAUDE.md").read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 40


def test_workflows_are_valid_yaml_with_jobs():
    files = glob.glob(str(ROOT / ".github" / "workflows" / "*.yml"))
    assert files
    for f in files:
        doc = yaml.safe_load(open(f, encoding="utf-8"))
        assert doc.get("jobs"), f


def test_no_private_strings_in_published_trees():
    from iif.data.scrub import find_private_strings

    hits = []
    for sub in ("data/legacy", "notebooks", "docs"):
        hits += find_private_strings(ROOT / sub)
    assert hits == []


def test_las_superficies_publicas_no_se_contradicen():
    """Lo que el sitio, el README y la ficha de cita afirman tiene que ser lo mismo (B-052).

    Son tres archivos que nadie recorre junto y que se escribieron en momentos distintos: el sitio decía
    que las fases 2 y 3 estaban sin terminar mientras el README publicaba sus resultados, y `CITATION.cff`
    apuntaba a un despliegue que ADR-005 adenda 5 manda borrar, de modo que quien citara el trabajo
    obtendría un enlace muerto.
    """
    retirada = "financial-inclusion-colombia.vercel.app"
    superficies = ["README.md", "README.es.md", "CITATION.cff", "index.qmd", "_quarto.yml"]
    con_url_muerta = [f for f in superficies if retirada in (ROOT / f).read_text(encoding="utf-8")]
    assert not con_url_muerta, f"apuntan al despliegue retirado (ADR-005, adenda 5): {con_url_muerta}"

    # El semáforo del sitio no puede declarar pendiente una fase cuyos resultados el README publica.
    index = (ROOT / "index.qmd").read_text(encoding="utf-8")
    for fase in (2, 3):
        fila = [ln for ln in index.splitlines() if ln.startswith(f"| {fase} |")]
        assert fila, f"no se encontró la fila de la fase {fase} en index.qmd"
        assert "pendiente" not in fila[0] and "en curso" not in fila[0], (
            f"index.qmd declara la fase {fase} sin terminar, pero el README publica sus resultados: {fila[0]}"
        )

    # Y ningún README puede anunciar que todavía no hay resultados y publicarlos más abajo.
    for archivo in ("README.md", "README.es.md"):
        texto = (ROOT / archivo).read_text(encoding="utf-8")
        assert "No results are published yet" not in texto, archivo
        assert "todavía no hay resultados" not in texto, archivo


def test_cada_adr_del_directorio_aparece_en_su_indice():
    """Un ADR que no está en el índice es una decisión que nadie encuentra (R-11)."""
    directorio = ROOT / "docs" / "decisiones"
    archivos = sorted(p.name for p in directorio.glob("ADR-*.md"))
    indice = (directorio / "README.md").read_text(encoding="utf-8")
    faltan = [a for a in archivos if a not in indice]
    assert not faltan, f"ADR sin entrada en docs/decisiones/README.md: {faltan}"


def test_every_source_in_manifest_is_registered():
    from iif.acquire.manifest import read_records
    from iif.acquire.sources import load_sources

    known = set(load_sources())
    unknown = {r.source_id for r in read_records()} - known
    assert unknown == set()
