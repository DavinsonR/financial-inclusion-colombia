import json
import zipfile

from iif import config
from iif.data.scrub import find_private_strings


def test_legacy_artifacts_exist():
    assert config.LEGACY_XLSX.exists() and config.LEGACY_PARQUET.exists()
    assert (config.DATA_LEGACY / "SHA256SUMS").exists()


def test_xlsx_metadata_is_clean():
    with zipfile.ZipFile(config.LEGACY_XLSX) as zf:
        core = zf.read("docProps/core.xml").decode("utf-8", "ignore")
        wb = zf.read("xl/workbook.xml").decode("utf-8", "ignore")
    assert "NOVOA" not in core.upper()
    assert "absPath" not in wb


def test_no_private_strings_anywhere():
    hits = []
    for root in (config.DATA_LEGACY, config.REPO_ROOT / "notebooks", config.DOCS_DIR / "legacy"):
        hits += find_private_strings(root)
    assert hits == []


def test_notebook_has_no_outputs_and_clean_kernel():
    nb = json.loads(
        (config.REPO_ROOT / "notebooks/legacy/TESIS_CONSOLIDADO.ipynb").read_text(encoding="utf-8")
    )
    assert len(nb["cells"]) == 24
    assert all(not c.get("outputs") for c in nb["cells"] if c["cell_type"] == "code")
    assert nb["metadata"]["kernelspec"]["name"] == "python3"
    src = "".join("".join(c["source"]) for c in nb["cells"])
    assert "coderdav" not in src and "../../data/legacy/" in src


def test_parquet_shape():
    import pandas as pd

    df = pd.read_parquet(config.LEGACY_PARQUET)
    assert df.shape == (462, 102)
