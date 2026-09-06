#!/usr/bin/env bash
# Carga en BigQuery los Parquet del repositorio. Idempotente: cada tabla se reemplaza.
# Uso: bash bigquery/01_load_parquet.sh <PROYECTO> [UBICACION]
# Requiere `bq` (SDK de gcloud) autenticado. El esquema se autodetecta del Parquet, que ya lleva los tipos.
set -euo pipefail

PROJECT="${1:?falta el id del proyecto de BigQuery}"
LOCATION="${2:-us-central1}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

bq --project_id="$PROJECT" --location="$LOCATION" query --use_legacy_sql=false < "$ROOT/bigquery/00_project_datasets.sql"

load_dir () {                      # <dataset> <tabla> <glob de Parquet>
  local dataset="$1" table="$2" glob="$3"
  echo "→ ${dataset}.${table}"
  # shellcheck disable=SC2086
  bq --project_id="$PROJECT" --location="$LOCATION" load \
     --source_format=PARQUET --replace --autodetect \
     "${dataset}.${table}" $glob
}

# Descargas SODA: un directorio por fuente, particionado por año. BigQuery acepta comodines en la ruta local.
for src in sfc_ptgf_ywrb sfc_kx2f_xjdq sfc_vkbt_desu mintic_n48w_gutb men_nudc_7mev; do
  [ -d "$ROOT/data/raw/$src" ] || { echo "  (falta data/raw/$src, se omite)"; continue; }
  load_dir raw "$src" "$ROOT/data/raw/$src/anio=*/part-0.parquet"
done

# Parquet tidy del DANE y del MGN
for f in "$ROOT"/data/interim/dane/*.parquet; do
  [ -e "$f" ] || break
  load_dir interim "$(basename "$f" .parquet)" "$f"
done
for f in "$ROOT"/data/interim/mgn/*.parquet; do
  [ -e "$f" ] || break
  load_dir interim "mgn_$(basename "$f" .parquet)" "$f"
done

echo
echo "Cargado. Tamaño por tabla:"
bq --project_id="$PROJECT" query --use_legacy_sql=false \
  "select table_schema, table_name, round(sum(total_logical_bytes)/1e6, 1) as mb
   from region-${LOCATION%%-*}.INFORMATION_SCHEMA.TABLE_STORAGE
   where table_schema in ('raw','interim') group by 1,2 order by mb desc"
