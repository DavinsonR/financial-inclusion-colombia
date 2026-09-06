# ADR-014 · Snowflake en producción, DuckDB en local y CI

- Fecha: 2026-09-06
- Estado: propuesta (la configuración queda escrita y marcada "sin probar contra una cuenta" hasta que existan credenciales)

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
