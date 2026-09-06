# BigQuery: warehouse en la nube del proyecto

**Por qué BigQuery y no otro.** El sandbox de BigQuery es gratuito de forma permanente y **sin tarjeta de
crédito**: 10 GB de almacenamiento activo y 1 TB de consulta al mes. Este proyecto entero pesa menos de
100 MB y sus consultas más pesadas escanean unos pocos cientos de MB, así que cabe con holgura en el nivel
gratuito y no puede generar una factura sorpresa. Es, además, el warehouse que piden muchas ofertas de
ingeniería y analítica de datos.

Comparación honesta con las otras opciones (ADR-014): Snowflake no tiene nivel gratuito permanente y queda
como demo posterior; DuckDB sigue siendo el motor de local, CI y del sitio, y no depende de que exista una
cuenta en la nube.

## Qué demuestra

| Pieza | Dónde | Por qué importa |
|---|---|---|
| Proyecto, datasets por capa y ubicación regional | `00_project_datasets.sql` | separación raw / staging / intermediate / marts, la misma que en DuckDB |
| Carga de Parquet desde el repositorio | `01_load_parquet.sh` | `bq load` con autodetección de esquema desde Parquet, particionado por año |
| Tablas particionadas y agrupadas | `02_partitioning_clustering.sql` | el equivalente en BigQuery a un índice: partición por fecha y `CLUSTER BY` por departamento |
| Control de coste explícito | `03_cost_controls.sql` | cuota de bytes por consulta y por usuario, y la consulta que mide el gasto real |
| Vistas autorizadas y control de acceso | `04_authorized_views.sql` | publicar marts sin dar acceso a las tablas crudas |
| dbt con el objetivo `bigquery` | `dbt/profiles.yml` | los mismos modelos y pruebas que en DuckDB |

## Cómo levantarlo

Requisitos: una cuenta de Google y el SDK de `gcloud` con `bq`. Sin tarjeta: al crear el proyecto se elige
el **sandbox** (sin cuenta de facturación asociada).

```bash
gcloud auth login
gcloud config set project <TU_PROYECTO>
bash bigquery/01_load_parquet.sh <TU_PROYECTO>      # crea datasets y carga data/raw y data/interim
bq query --use_legacy_sql=false < bigquery/02_partitioning_clustering.sql
```

Después, dbt contra BigQuery:

```bash
export IIF_DBT_TARGET=bigquery BIGQUERY_PROJECT=<TU_PROYECTO> BIGQUERY_LOCATION=us-central1
export GOOGLE_APPLICATION_CREDENTIALS=/ruta/a/la/clave.json   # o `gcloud auth application-default login`
uv run dbt build --profiles-dir dbt --project-dir dbt --target bigquery
```

## Límite del sandbox

Sin cuenta de facturación, BigQuery aplica una **expiración de 60 días** a toda tabla y partición: los datos
se borran solos. Para este proyecto es aceptable, porque las tablas se reconstruyen desde el repositorio con
un solo comando. Si en algún momento se asocia facturación, la expiración desaparece y `02_partitioning_clustering.sql`
deja de necesitar el recordatorio.

## Estado

Los scripts están escritos y revisados, **sin ejecutar contra un proyecto real** (esta sesión no tiene
credenciales de Google). La primera ejecución puede exigir ajustes de nombres de dataset o de ubicación;
lo que salga se anota en la bitácora.
