#!/usr/bin/env python3
"""¿Reproduce el código actual los artefactos publicados en `data/processed`?

Sustituye a un `git diff --quiet` sobre esa carpeta, que no podía funcionar y se
midió por qué:

  · los dos JSON de `econ/` llevan dentro `generado_en` con la hora de
    generación, así que nunca salen iguales dos veces;
  · los parquet del índice salían con las filas en otro orden en cada máquina
    (consulta a DuckDB sin ORDER BY, y DuckDB paraleliza), y además con ruido de
    último bit — alineadas por clave, la mayor diferencia medida entre dos
    entornos fue 1,4e-14.

Ninguna de las dos cosas es una cifra distinta. Comparar bytes las confundía con
un cambio de resultado, que es el peor error que puede cometer una comprobación
de reproducibilidad: enseña a ignorarla.

Así que se compara contenido con tolerancia, con el mismo criterio que ya usa
`tests/test_resultados_publicados.py`: `generado_en` fuera, tolerancia 1e-6. Una
cifra que de verdad se mueva sigue poniendo esto en rojo.

Uso:  uv run python scripts/check_processed.py
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"

# Ruta relativa al repositorio -> columnas que identifican una fila.
PARQUETS = {
    "data/processed/indice_departamento_anual.parquet": ["dpto_ccdgo", "anio"],
    "data/processed/indice_municipio_anual.parquet": ["mpio_ccdgo", "anio"],
}
JSONS = [
    "data/processed/econ/resultados.json",
    "data/processed/econ/curva_especificacion.json",
]

# Claves cuyo valor cambia en cada corrida por diseño. Mismo nombre y mismo
# criterio que en tests/test_resultados_publicados.py.
VOLATILES = {"generado_en"}
TOL = 1e-6


def publicado(ruta: str) -> bytes | None:
    """El fichero tal como está en HEAD, sin tocar el árbol de trabajo."""
    r = subprocess.run(["git", "show", f"HEAD:{ruta}"], cwd=ROOT, capture_output=True)
    return r.stdout if r.returncode == 0 else None


def difieren_json(a, b, ruta: str = "") -> list[str]:
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            if k in VOLATILES:
                continue
            if k not in a or k not in b:
                out.append(f"{ruta}.{k}: solo en {'publicado' if k in a else 'regenerado'}")
            else:
                out += difieren_json(a[k], b[k], f"{ruta}.{k}")
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{ruta}: {len(a)} elementos publicados contra {len(b)}"]
        out = []
        for i, (x, y) in enumerate(zip(a, b, strict=True)):
            out += difieren_json(x, y, f"{ruta}[{i}]")
        return out
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        if math.isnan(float(a)) and math.isnan(float(b)):
            return []
        if abs(float(a) - float(b)) > TOL * max(1.0, abs(float(a))):
            return [f"{ruta}: {a} -> {b}"]
        return []
    return [] if a == b else [f"{ruta}: {a!r} -> {b!r}"]


def main() -> int:
    problemas: list[str] = []
    import io as _io

    for ruta, ids in PARQUETS.items():
        crudo = publicado(ruta)
        if crudo is None:
            problemas.append(f"{ruta}: no está en HEAD")
            continue
        try:
            a = pd.read_parquet(_io.BytesIO(crudo))
            b = pd.read_parquet(ROOT / ruta)
        except Exception as exc:  # noqa: BLE001
            problemas.append(f"{ruta}: no se pudo leer ({exc})")
            continue

        if list(a.columns) != list(b.columns):
            problemas.append(f"{ruta}: las columnas cambiaron")
            continue
        # El orden de filas NO se compara: no lo promete nadie y ordenar por la
        # clave es justo lo que hace `iif index` antes de escribir.
        a = a.sort_values(ids).reset_index(drop=True)
        b = b.sort_values(ids).reset_index(drop=True)
        if not a[ids].equals(b[ids]):
            problemas.append(f"{ruta}: el conjunto de filas cambió")
            continue
        for c in a.columns:
            if c in ids:
                continue
            if pd.api.types.is_numeric_dtype(a[c]):
                x, y = a[c].to_numpy(float), b[c].to_numpy(float)
                d = pd.Series(abs(x - y)).max()
                escala = max(1.0, float(pd.Series(abs(x)).max() or 0))
                if d > TOL * escala:
                    problemas.append(f"{ruta}: columna {c} difiere hasta {d:.3e}")
            elif not a[c].equals(b[c]):
                problemas.append(f"{ruta}: columna {c} difiere")

    for ruta in JSONS:
        crudo = publicado(ruta)
        if crudo is None:
            problemas.append(f"{ruta}: no está en HEAD")
            continue
        try:
            a = json.loads(crudo.decode("utf-8"))
            b = json.loads((ROOT / ruta).read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            problemas.append(f"{ruta}: no se pudo leer ({exc})")
            continue
        for d in difieren_json(a, b)[:10]:
            problemas.append(f"{ruta}{d}")

    if problemas:
        print(f"x data/processed: el codigo no reproduce lo publicado ({len(problemas)} problema(s))\n")
        for p in problemas:
            print(f"  - {p}")
        print("\n  Si el cambio es intencionado, regenera y commitea:")
        print("    make dbt-build && uv run python -m iif.cli index && uv run python -m iif.cli econ && uv run python -m iif.cli curva")
        return 1

    print("ok data/processed: el codigo reproduce lo publicado "
          f"(tolerancia {TOL:g}, sin contar {', '.join(sorted(VOLATILES))} ni el orden de filas)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
