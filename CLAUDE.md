# CLAUDE.md · financial-inclusion-colombia
Proyecto de investigación reproducible sobre inclusión financiera y crecimiento regional en Colombia; el trabajo de grado de 2026 es el origen. Guía completa: docs/GUIA_DEL_PROYECTO.md. Errores y aciertos: docs/BITACORA_AGENTE.md.

## Reglas duras
- R-01 Docs internas y mensajes de commit en español, sin emojis. `README.md` en inglés y `README.es.md` al lado, con las mismas anclas. Identificadores, columnas y nombres de módulos en inglés.
- R-02 Solo `uv` (`uv sync`, `uv run`, `uv add`). Nunca `pip install`.
- R-03 `make check` (ruff, pytest, dbt build en DuckDB, quarto render) antes de cualquier commit.
- R-04 Nunca rutas absolutas. Todo cuelga de `iif.config` (`REPO_ROOT`, `DATA_RAW`, `SEEDS_DIR`, ...).
- R-05 Nunca repetir un valor anual en cuatro trimestres. El grano de estimación es anual (ADR-001).
- R-06 `data/legacy/`, `notebooks/legacy/` y `paper/` están congelados: solo lectura.
- R-07 Ningún archivo > 45 MB en git. Toda descarga pasa por `iif acquire` y queda en `data/raw/manifest.jsonl`.
- R-08 Nunca PII: ni nombre legal completo del autor en metadatos, ni rutas locales, ni correos.
- R-09 Toda cifra publicada en docs o sitio traza a una prueba, a una fila del libro de verificación o a un test dbt.
- R-10 Antes de arreglar un error, entrada en la bitácora (id, causa raíz, regla). Después, el arreglo.
- R-11 Las decisiones de valor van a un ADR en `docs/decisiones/` antes del código.
- R-12 El README conserva las anclas `status abstract data method main-result diagnostics que-hay-y-que-falta`.
- R-13 Los ceros de SFC y MEN son faltantes, salvo dentro del bloque de la fila (ADR-008).
- R-14 Los datos derivados de SFC, MinTIC y MEN son CC BY-SA 4.0: atribuir y compartir igual (ADR-012).
- R-15 Una sola fuente de verdad por constante: `dbt/seeds/*.csv` o `config/*.yaml`. Sin mapas duplicados en Python.
- R-16 Una sesión termina con pruebas verdes, bitácora al día y hoja de ruta de la guía marcada.
- R-17 Antes de elegir un método se mide su supuesto (KMO < 0,5 descarta PCA); el índice publica sus pesos implícitos y ninguno puede ser negativo (ADR-015).

## Comandos
- `make setup`           dependencias con uv y kernel de Jupyter
- `make quarto-install`  Quarto por tarball (la API de GitHub puede estar bloqueada)
- `make check`           ruff + pytest + dbt build (DuckDB) + quarto render
- `make reproduce`       pipeline legado → docs/legacy/reproduccion.md
- `make acquire`         descarga todas las fuentes de config/sources.yaml
- `make render`          sitio Quarto en _site/

## Dónde está qué
- `src/iif/`             paquete: config, cli, acquire, parse, crosswalk, index, econ, export, data, legacy
- `dbt/`                 estrella dimensional: seeds, staging, intermediate, marts, tests; objetivos duckdb y snowflake
- `config/`              `tesis_documento.yaml` (cifras del documento), `sources.yaml`, `index.yaml`, `atlas.yaml`
- `docs/decisiones/`     ADR-001 … ADR-016, índice en su README.md
- `docs/BITACORA_AGENTE.md` errores B-NNN y aciertos S-NNN · `docs/GUIA_DEL_PROYECTO.md` control del autor
