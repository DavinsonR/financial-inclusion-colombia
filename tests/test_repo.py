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


def test_every_source_in_manifest_is_registered():
    from iif.acquire.manifest import read_records
    from iif.acquire.sources import load_sources

    known = set(load_sources())
    unknown = {r.source_id for r in read_records()} - known
    assert unknown == set()
