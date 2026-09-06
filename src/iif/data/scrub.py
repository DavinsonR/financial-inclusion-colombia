"""Limpieza de los artefactos legados antes de publicarlos.

Lo que se quita: rutas absolutas de máquinas personales, metadatos de autor del xlsx
(nombre legal completo, ruta de Windows incrustada por Excel), salidas ejecutadas del
notebook y el nombre malformado del kernel. Lo que NO se toca: ni un solo valor de datos.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import nbformat
import openpyxl
import pandas as pd

PRIVATE_PATH_PATTERNS = (r"/home/coderdav", r"D:\\davin", r"Economy_Master", r"Economy Master")
LEGACY_RELATIVE_PATH = "../../data/legacy/panel_fintech_colombia_trimestral.xlsx"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def scrub_xlsx(src: Path, dst: Path) -> dict:
    """Re-guarda el libro con openpyxl (descarta `x15ac:absPath`) y resetea las propiedades."""
    wb = openpyxl.load_workbook(src)
    props = wb.properties
    props.creator = "Proyecto IIF Colombia"
    props.lastModifiedBy = "Proyecto IIF Colombia"
    props.title = "Panel departamental trimestral de la tesis (2017Q4-2021Q1), congelado"
    props.description = "Artefacto legado. Los valores no se modifican; solo se limpian metadatos."
    dst.parent.mkdir(parents=True, exist_ok=True)
    wb.save(dst)
    df = pd.read_excel(dst)
    parquet = dst.with_suffix(".parquet")
    df.to_parquet(parquet, index=False)
    return {"rows": int(df.shape[0]), "cols": int(df.shape[1]), "xlsx": dst, "parquet": parquet}


def scrub_notebook(src: Path, dst: Path) -> dict:
    nb = nbformat.read(src, as_version=4)
    replaced = 0
    for cell in nb.cells:
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None
            new = re.sub(
                r'RUTA_DATOS\s*=\s*r?["\'].*?["\']',
                f'RUTA_DATOS = "{LEGACY_RELATIVE_PATH}"  # relativa a notebooks/legacy/',
                cell.source,
            )
            if new != cell.source:
                replaced += 1
                cell.source = new
        elif cell.cell_type == "markdown":
            new = cell.source.replace(
                "# Tesis Novoa Ramírez — Notebook consolidado",
                "# Notebook consolidado de la tesis (legado, congelado)",
            ).replace(
                "Reemplaza a `PCA_GMM_Fintech_Javeriana` y `Correcciones_Tesis_Novoa_Ramirez`.",
                "Reemplaza a dos notebooks anteriores del mismo trabajo. Se conserva tal como quedó "
                "en agosto de 2026; la versión mantenida vive en `src/iif/legacy/`.",
            )
            cell.source = new
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    nb.metadata.pop("language_info", None)
    dst.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb, dst)
    return {"cells": len(nb.cells), "paths_replaced": replaced, "dst": dst}


def scrub_markdown(src: Path, dst: Path) -> dict:
    lines = src.read_text(encoding="utf-8").splitlines()
    out, dropped = [], 0
    for line in lines:
        if any(re.search(p, line) for p in PRIVATE_PATH_PATTERNS):
            out.append(re.sub(r"[:]\s*/.*$|[:]\s*[A-Z]:\\.*$", ": [ruta local omitida]", line))
            dropped += 1
        else:
            out.append(line)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text("\n".join(out) + "\n", encoding="utf-8")
    return {"lines": len(out), "paths_masked": dropped, "dst": dst}


def find_private_strings(
    root: Path, needles=("NOVOA RAMIREZ", "absPath", "coderdav", "davin\\")
) -> list[str]:
    """Busca cadenas privadas en archivos de texto y dentro de los xlsx (zip) bajo `root`."""
    import zipfile

    hits: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix == ".xlsx":
            with zipfile.ZipFile(path) as zf:
                for name in ("docProps/core.xml", "xl/workbook.xml"):
                    if name in zf.namelist():
                        text = zf.read(name).decode("utf-8", "ignore")
                        hits += [f"{path}:{name}:{n}" for n in needles if n in text]
        elif path.suffix in {".md", ".ipynb", ".py", ".csv", ".txt", ".yaml", ".yml"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            hits += [f"{path}:{n}" for n in needles if n in text]
    return hits


def write_checksums(paths: list[Path], out: Path) -> None:
    out.write_text("".join(f"{sha256_of(p)}  {p.name}\n" for p in paths), encoding="utf-8")
