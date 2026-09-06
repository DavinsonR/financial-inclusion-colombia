# ADR-014 · DuckDB como motor, BigQuery como warehouse en la nube, Snowflake como demo posterior

- Fecha: 2026-09-06
- Estado: aceptada, con dos adendas del 2026-09-06: DuckDB es el motor del proyecto; BigQuery es el warehouse en la nube (sandbox gratuito); Snowflake queda como demo posterior

## Contexto

El autor quiere una tecnología nueva que sirva para cargos internacionales. Snowflake es el warehouse en la nube más demandado en ofertas de ingeniería y analítica de datos. No tiene nivel gratuito permanente: prueba de 30 días con 400 USD de crédito; después exige tarjeta o la cuenta se suspende. El proyecto no puede depender de que la cuenta siga viva. Lo público (sitio y atlas) no debe pasar por Snowflake.

## Decisión

1. dbt con dos objetivos en `dbt/profiles.yml`: `duckdb` (local y CI, por defecto) y `snowflake` (producción). Los mismos modelos; macros de dialecto donde haga falta (`read_parquet` frente a stage).
2. Coste controlado: warehouse X-Small, autosuspensión a 60 segundos, cargas solo cuando cambian los datos, y un resource monitor con tope mensual. Estimación: 3 a 10 USD al mes tras la prueba.
3. Lo que se demuestra, cada pieza con su motivo en `snowflake/README.md`: warehouse virtual y créditos; stage interno y `COPY INTO` desde los Parquet del repo; filas crudas de la API en `VARIANT` con `FLATTEN` (`raw_sfc_variant`); Time Travel y clonación sin copia como mecanismo de vintages para la revisión anual del DANE (`CREATE SCHEMA marts_v2026_07 CLONE marts`); RBAC con roles `loader`, `transformer` y `reader`; `dbt-snowflake` incremental con `merge`; dynamic tables opcionales.
4. Scripts en `snowflake/`: `00_roles.sql`, `01_warehouse_monitor.sql`, `02_stages_copy.sql`, `03_clone_vintage.sql`.
5. CI: el job `snowflake` corre `dbt build --target snowflake` solo si existen los secrets (`SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PRIVATE_KEY`, `SNOWFLAKE_ROLE`, `SNOWFLAKE_WAREHOUSE`). El job DuckDB corre siempre (B-020).
6. Lo público no pasa por Snowflake: el atlas lee exportaciones en `atlas/data/`. Un tablero PBIP de Power BI conectado a Snowflake es opcional.

## Alternativas consideradas

- BigQuery + Looker Studio: nivel gratuito permanente (10 GB de almacenamiento y 1 TB de consulta al mes), sin tarjeta obligatoria para el sandbox; menos demandado que Snowflake en las ofertas que interesan al autor. Es la alternativa si la cuenta de Snowflake se suspende.
- Databricks Free Edition: gratuito, orientado a Spark y notebooks; el modelo de warehouse SQL es menos central.
- Solo DuckDB con MotherDuck: gratuito hasta cierto tamaño, muy simple; no demuestra un warehouse de producción.
- Postgres gestionado: no demuestra separación de cómputo y almacenamiento ni vintages por clonación.

## Consecuencias

- Todo corre sin Snowflake; Snowflake añade la demostración y una copia de producción.
- El autor decide en 30 días si pone tarjeta. Si no, el ADR pasa a "reemplazada" por BigQuery o se queda solo DuckDB, sin tocar los modelos.
- Los secrets viven en GitHub Actions; nunca en el repo (`.p8` y `.pem` están en `.gitignore`).

## Cómo revertirla

Borrar el objetivo `snowflake` de `profiles.yml`, el job de CI y la carpeta `snowflake/`. Nada más depende de ellos.

## Adenda 2026-09-06: decisión del autor

El autor pidió dejar BigQuery y Databricks fuera de consideración y tratar Snowflake como un demo a posterior, no como producción. En consecuencia:

1. DuckDB es el motor del proyecto en local, en CI y para todo lo que publica el sitio. No hay "producción" separada.
2. `dbt/profiles.yml` conserva el objetivo `snowflake` y `snowflake/*.sql` se mantienen como material del demo; nada del proyecto los ejecuta.
3. El job `snowflake` de `ci.yml` se elimina; se recreará cuando exista el demo.
4. Databricks y MotherDuck quedan descartados por decisión del autor, no por análisis técnico nuevo.

## Adenda 2: BigQuery sí entra (2026-09-06, misma tarde)

El autor aclaró que sí quiere la implementación de BigQuery. Es la opción con mejor relación entre lo que
demuestra y lo que cuesta:

1. **Sandbox gratuito permanente y sin tarjeta**: 10 GB de almacenamiento activo y 1 TB de consulta al mes.
   El proyecto pesa menos de 100 MB, así que no puede generar factura. Snowflake, en cambio, exige tarjeta
   tras 30 días.
2. **Objetivo `bigquery` en `dbt/profiles.yml`**, con los mismos modelos, semillas y pruebas que DuckDB.
   `maximum_bytes_billed` fijado en 1 GB por consulta como tope duro.
3. **Scripts en `bigquery/`**: datasets por capa, carga de los Parquet del repositorio con `bq load`,
   particionado y agrupación de las cuatro tablas grandes, control de coste (cuotas y la consulta que mide
   el gasto real) y vistas autorizadas para publicar marts sin exponer las tablas crudas.
4. **CI**: el job `bigquery` corre `dbt build --target bigquery` en `main` solo si existen los secrets
   `BIGQUERY_PROJECT`, `BIGQUERY_LOCATION` y `BIGQUERY_KEYFILE_JSON`. El job DuckDB corre siempre.
5. **Límite conocido del sandbox**: sin cuenta de facturación, toda tabla y partición expira a los 60 días.
   Aceptable porque las tablas se reconstruyen desde el repositorio con un comando; queda escrito en
   `bigquery/README.md` para que nadie lo descubra por sorpresa.
6. Lo público (sitio y atlas) sigue sin pasar por ninguna nube: sale de DuckDB y de los Parquet del repo.
