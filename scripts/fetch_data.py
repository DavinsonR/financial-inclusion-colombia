#!/usr/bin/env python3
"""Baja la instantánea de `data/raw/` desde el Release de GitHub y la verifica.

Por qué existe: esas 53 descargas pesaban 121 MB de los 124 MB del repositorio,
así que un clon completo obligaba a bajarlas aunque solo se quisiera leer el
código. Salieron del historial y viven en un Release; este script las devuelve.

Solo biblioteca estándar, a propósito: tiene que correr ANTES de `make setup`,
cuando todavía no hay entorno de `uv` ni dependencias instaladas.

Verifica dos veces, y las dos importan:
  1. el sha256 del tarball, contra la constante de aquí abajo — que el archivo
     que bajó es el que se publicó;
  2. cada fichero extraído, contra `data/raw/manifest.jsonl` — que los bytes
     son los mismos con los que se calcularon los resultados publicados.

La segunda es la que vale para la tesis. `make acquire` vuelve a descargar de
las fuentes originales, pero una fuente pública puede cambiar bajo los pies: el
manifiesto es lo que distingue «los datos de hoy» de «los datos con los que se
publicó».
"""

from __future__ import annotations

import hashlib
import json
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

URL = (
    "https://github.com/DavinsonR/financial-inclusion-colombia"
    "/releases/download/data-v1/iif-data-raw.tar.gz"
)
TARBALL_SHA256 = "3de592f4cc4f221a353830c63c129bbce3fbc7bf4ab8839b7d4ed76601602ecc"

ROOT = Path(__file__).resolve().parent.parent
# Segundos sin recibir bytes antes de abandonar. Sin esto, una conexion colgada deja a CI esperando
# hasta su propio timeout de 25 minutos sin decir por que.
TIMEOUT_S = 60
MANIFEST = ROOT / "data" / "raw" / "manifest.jsonl"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(dest: Path) -> None:
    print(f"bajando  {URL}")
    with urllib.request.urlopen(URL, timeout=TIMEOUT_S) as resp:  # noqa: S310 — URL fija, https, del propio repositorio
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        with open(dest, "wb") as fh:
            while chunk := resp.read(1 << 20):
                fh.write(chunk)
                done += len(chunk)
                if total:
                    pct = 100 * done / total
                    print(f"\r  {done / 1048576:6.1f} / {total / 1048576:.1f} MB  {pct:5.1f}%",
                          end="", flush=True)
        print()


def verify_against_manifest() -> list[str]:
    """Los mismos criterios que `iif manifest verify`, pero sin necesitar el entorno.

    El manifiesto solo crece: el último registro de cada fuente es su descarga
    vigente, y las anteriores quedan superadas. Comprobar las viejas daría
    falsos fallos por ficheros que ya se reemplazaron.
    """
    if not MANIFEST.exists():
        return [f"falta el manifiesto: {MANIFEST}"]

    records = [json.loads(line) for line in MANIFEST.read_text(encoding="utf-8").splitlines() if line.strip()]
    newest: dict[str, str] = {}
    for r in records:
        newest[r["source_id"]] = r["pull_id"]
    vigentes = [r for r in records if r["pull_id"] == newest[r["source_id"]]]

    problems = []
    for r in vigentes:
        p = ROOT / r["path"]
        if not p.exists():
            problems.append(f"falta {r['path']}")
        elif r.get("sha256") and sha256_of(p) != r["sha256"]:
            problems.append(f"sha256 distinto en {r['path']}")
    print(f"manifiesto: {len(vigentes)} ficheros vigentes comprobados")
    return problems


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tarball = Path(tmp) / "iif-data-raw.tar.gz"
        download(tarball)

        got = sha256_of(tarball)
        if got != TARBALL_SHA256:
            print(f"ERROR: sha256 del tarball no coincide\n  esperado {TARBALL_SHA256}\n  obtenido {got}",
                  file=sys.stderr)
            return 1
        print("tarball: sha256 correcto")

        # `data/raw/README.md` y `manifest.jsonl` sí están versionados. El tarball
        # trae el README; extraerlo lo reescribe con los mismos bytes, así que no
        # ensucia el árbol. El manifiesto no viaja en el tarball justamente para
        # que no se pueda sobrescribir con una copia sin firmar.
        print("extrayendo en data/raw/")
        with tarfile.open(tarball) as tf:
            miembros = [m for m in tf.getmembers() if not m.name.endswith("manifest.jsonl")]
            if hasattr(tarfile, "data_filter"):  # Python 3.12+: rechaza rutas fuera del destino
                tf.extractall(ROOT, members=miembros, filter="data")
            else:
                # Python 3.11 (el de CI) no tiene `filter`: la misma guarda, a mano. Solo ficheros y
                # directorios, y todos dentro del repositorio.
                raiz = ROOT.resolve()
                for m in miembros:
                    destino = (raiz / m.name).resolve()
                    if not (m.isfile() or m.isdir()) or not destino.is_relative_to(raiz):
                        print(f"ERROR: miembro no permitido en el tarball: {m.name}", file=sys.stderr)
                        return 1
                tf.extractall(ROOT, members=miembros)  # noqa: S202

    problems = verify_against_manifest()
    if problems:
        print("\nERROR: los datos extraídos no cuadran con el manifiesto:", file=sys.stderr)
        for p in problems:
            print(f"  · {p}", file=sys.stderr)
        return 1

    tamano = sum(f.stat().st_size for f in (ROOT / "data" / "raw").rglob("*") if f.is_file())
    print(f"listo: data/raw/ con {tamano / 1048576:.0f} MB, verificado contra el manifiesto")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
