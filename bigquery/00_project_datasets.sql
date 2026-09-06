-- 00_project_datasets.sql — datasets por capa, con la misma separación que en DuckDB.
-- Ejecutar con: bq query --use_legacy_sql=false --project_id=<TU_PROYECTO> < bigquery/00_project_datasets.sql
-- La ubicación se fija al crear cada dataset y no se puede cambiar después: usar la misma en todos.

CREATE SCHEMA IF NOT EXISTS `raw`
  OPTIONS (location = 'us-central1',
           description = 'Cargas crudas: Parquet de data/raw (SFC, MinTIC, MEN) tal como los escribió `iif acquire`');

CREATE SCHEMA IF NOT EXISTS `interim`
  OPTIONS (location = 'us-central1',
           description = 'Parquet tidy de data/interim: anexos del DANE y atributos del MGN parseados por `iif parse`');

CREATE SCHEMA IF NOT EXISTS `staging`
  OPTIONS (location = 'us-central1', description = 'dbt: vistas de limpieza y tipado');

CREATE SCHEMA IF NOT EXISTS `intermediate`
  OPTIONS (location = 'us-central1', description = 'dbt: empalmes, unpivot y claves aplicadas');

CREATE SCHEMA IF NOT EXISTS `seeds`
  OPTIONS (location = 'us-central1', description = 'dbt: semillas (crosswalks y diccionarios)');

CREATE SCHEMA IF NOT EXISTS `marts`
  OPTIONS (location = 'us-central1', description = 'dbt: dimensiones, hechos y marts de análisis');
