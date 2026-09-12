# Comandos del proyecto. `make check` es lo que corre CI y lo que se exige antes de cada commit.
export IIF_ROOT := $(CURDIR)
export IIF_DUCKDB_PATH ?= $(CURDIR)/db/iif.duckdb
export QUARTO_PYTHON := $(CURDIR)/.venv/bin/python
DBT_FLAGS := --profiles-dir dbt --project-dir dbt

.PHONY: setup quarto-install lint test test-data dbt-build reproduce render check acquire parse index econ curva atlas manifest clean

setup:            ## dependencias de Python (uv) y kernel de Jupyter
	uv sync --all-groups --all-extras
	uv run python -m ipykernel install --user --name python3 --display-name "Python (iif)"

quarto-install:   ## Quarto desde el tarball de GitHub
	bash scripts/install_quarto.sh

lint:             ## ruff y YAML de los workflows
	uv run ruff check .
	uv run python -c "import glob,yaml;[yaml.safe_load(open(f)) for f in glob.glob('.github/workflows/*.yml')]"

test:             ## pruebas sin datos crudos
	uv run pytest -m "not data"

test-data:        ## pruebas que leen data/raw (se saltan si no hay datos)
	uv run pytest -m data

dbt-build:        ## semillas + modelos + pruebas en DuckDB
	uv run dbt deps $(DBT_FLAGS)
	uv run dbt seed $(DBT_FLAGS)
	uv run dbt build $(DBT_FLAGS)

reproduce:        ## corre el pipeline legado y escribe el informe en markdown
	uv run iif reproduce --out docs/legacy/reproduccion.md

render:           ## sitio Quarto
	quarto render

check: lint test dbt-build render

acquire:          ## descarga todas las fuentes registradas en config/sources.yaml
	uv run iif acquire all

parse:            ## XLSX/GeoJSON del DANE y MGN a Parquet tidy
	uv run iif parse dane
	uv run iif parse mgn

index:            ## construye el índice de inclusión financiera (ADR-015, ADR-017)
	uv run iif index

econ:             ## corre la batería econométrica y escribe resultados.json (ADR-016, ADR-018)
	uv run iif econ

curva:            ## estima la curva de especificación (ADR-018)
	uv run iif curva

atlas:            ## exporta la geometría y las series del atlas (ADR-005)
	uv run iif atlas

manifest:
	uv run iif manifest verify

clean:
	rm -rf _site .quarto dbt/target dbt/logs db/*.duckdb
