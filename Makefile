# Comandos del proyecto. `make check` es lo que corre CI y lo que se exige antes de cada commit.
export IIF_ROOT := $(CURDIR)
export IIF_DUCKDB_PATH ?= $(CURDIR)/db/iif.duckdb
# El Python del entorno de uv vive en .venv/bin en Linux y macOS, y en .venv/Scripts en Windows.
ifeq ($(OS),Windows_NT)
VENV_PYTHON := $(CURDIR)/.venv/Scripts/python.exe
else
VENV_PYTHON := $(CURDIR)/.venv/bin/python
endif
export QUARTO_PYTHON ?= $(VENV_PYTHON)
DBT_FLAGS := --profiles-dir dbt --project-dir dbt

.PHONY: help setup quarto-install lint test test-data dbt-build reproduce render check data acquire parse index forecast atlas manifest clean

help:             ## lista los targets con su descripcion
	@grep -E '^[a-z-]+:.*## ' Makefile | sed 's/:.*## /	/'

setup:            ## dependencias de Python (uv) y kernel de Jupyter
	uv sync --all-groups --all-extras
	uv run python -m ipykernel install --user --name python3 --display-name "Python (iif)"

quarto-install:   ## Quarto desde el tarball de GitHub
	bash scripts/install_quarto.sh

lint:             ## ruff y YAML de los workflows
	uv run ruff check .
	uv run python -c "import glob,yaml;[yaml.safe_load(open(f,encoding='utf-8')) for f in glob.glob('.github/workflows/*.yml')]"

test:             ## pruebas sin datos crudos
	uv run pytest -m "not data"

test-data:        ## pruebas que leen data/raw (se saltan si no hay datos)
	uv run pytest -m data -rs

dbt-build:        ## semillas + modelos + pruebas en DuckDB
	uv run dbt deps $(DBT_FLAGS)
	uv run dbt seed $(DBT_FLAGS)
	uv run dbt build $(DBT_FLAGS)

reproduce:        ## corre el pipeline legado y escribe el informe en markdown
	uv run iif reproduce --out docs/legacy/reproduccion.md

render:           ## sitio Quarto
	quarto render

check: lint test dbt-build render

# fetch_data.py usa solo la biblioteca estandar: corre antes de `make setup`, sin instalar el proyecto,
# y pasa por uv (R-02) en vez de por un `python3` que en Windows puede no existir.
data:             ## baja data/raw desde el Release y lo verifica contra el manifiesto
	uv run --no-project python scripts/fetch_data.py

acquire:          ## descarga todas las fuentes registradas en config/sources.yaml
	uv run iif acquire all

parse:            ## XLSX/GeoJSON del DANE y MGN a Parquet tidy
	uv run iif parse dane
	uv run iif parse mgn

index:            ## construye el índice de inclusión financiera (ADR-015)
	uv run iif index

forecast:         ## capa de proyeccion del crecimiento departamental (ADR-019 a ADR-022)
	uv run iif forecast

atlas:            ## exporta atlas/data/*.json desde config/atlas.yaml (ADR-005)
	uv run iif atlas

manifest:         ## verifica data/raw contra data/raw/manifest.jsonl
	uv run iif manifest verify

clean:            ## borra salidas regenerables (no toca data/, _freeze ni atlas/data)
	rm -rf _site .quarto dbt/target dbt/logs dbt/dbt_packages db/*.duckdb db/*.duckdb.wal .pytest_cache .ruff_cache
