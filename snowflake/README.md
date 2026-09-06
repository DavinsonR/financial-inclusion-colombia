# Snowflake: material para un demo posterior

**Estado (2026-09-06): demo a posterior, sin fecha. El proyecto corre solo en DuckDB (ADR-014, adenda).** Los scripts siguen sin probarse contra una cuenta real. Estos scripts se escribieron y revisaron sin credenciales;
se ejecutarán y corregirán la primera vez que exista la cuenta de prueba (30 días / 400 USD). Hasta
entonces todo el proyecto corre en DuckDB (`make dbt-build`), que es el objetivo por defecto de dbt y el que
usa CI. Nada del sitio ni de la reproducción depende de que Snowflake exista o siga vivo.

## Para qué

Snowflake es el objetivo `snowflake` de `dbt/profiles.yml`: los mismos modelos, semillas y pruebas que
en DuckDB, en un warehouse compartido con control de acceso, historial (Time Travel) y clones por
vintage para la revisión anual del DANE. Sirve como respaldo de producción y como conexión para un tablero
de Power BI; lo público (atlas en Quarto/OJS) se construye desde exportaciones Parquet y no lo toca.

## Control de coste, dicho claro

- Sin nivel gratuito permanente. Tras la prueba exige tarjeta; si no hay, la cuenta se suspende y el
  proyecto sigue en DuckDB sin cambios.
- Un solo warehouse **X-Small** (`WH_IIF_XS`): 1 crédito/hora solo mientras está activo, autosuspensión
  a los 60 s, arranque suspendido.
- **Resource monitor** `RM_IIF`: 10 créditos al mes; aviso al 75 %, suspensión al 100 %, corte inmediato al 110 %.
- Cargas solo cuando cambian los datos (los Parquet del repositorio son la fuente; Snowflake no descarga nada).
- Estimación con ese uso: 3-10 USD/mes. Seguimiento: `SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY`.

## Qué hace cada script

| Script | Rol para ejecutarlo | Qué crea |
|---|---|---|
| `00_roles_and_users.sql` | ACCOUNTADMIN (USERADMIN + SECURITYADMIN) | Roles `LOADER`, `TRANSFORMER`, `READER`; usuario de servicio `DBT` con clave RSA (marcador a reemplazar); jerarquía y grants de roles |
| `01_warehouse_and_monitor.sql` | ACCOUNTADMIN | Warehouse `WH_IIF_XS` (X-Small, auto_suspend 60 s, auto_resume) y resource monitor `RM_IIF` (10 créditos/mes, 75 % notify, 100 % suspend) |
| `02_database_stages_copy.sql` | SYSADMIN | Base `IIF`; esquemas `RAW`, `STAGING`, `INTERMEDIATE`, `SEEDS`, `MARTS`; formato Parquet; stage interno `RAW.STG_PARQUET`; ejemplo `PUT` + `COPY INTO RAW.SFC_KX2F_XJDQ ... MATCH_BY_COLUMN_NAME`; tabla `RAW.SFC_VARIANT` (JSON crudo de la API) con vista `FLATTEN`; permisos por rol |
| `03_clone_vintage.sql` | TRANSFORMER | `CREATE SCHEMA MARTS_V2026_07 CLONE MARTS` (clon zero-copy), consultas Time Travel `AT (TIMESTAMP => ...)` y diff entre vintages |
| `04_dynamic_table_example.sql` | TRANSFORMER | Dynamic table `MARTS.DT_INCLUSION_DEPARTAMENTO_ANUAL` con `TARGET_LAG = '1 day'` que anualiza los hechos trimestrales según `dim_variable.regla_anualizacion` |

Los scripts son idempotentes donde Snowflake lo permite (`CREATE ... IF NOT EXISTS`, `GRANT` repetible).
`COPY INTO` no es idempotente en sentido estricto: carga los archivos del stage que aún no haya cargado
(Snowflake recuerda 64 días); una recarga completa exige `TRUNCATE` + `COPY INTO ... FORCE = TRUE`.

## Cómo se ejecutan una sola vez (autor)

1. Crear la cuenta de prueba y anotar el identificador (`<org>-<cuenta>`).
2. Generar el par de claves fuera del repositorio (el `.p8` está en `.gitignore`):
   `openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out rsa_key.p8 -nocrypt` y
   `openssl rsa -in rsa_key.p8 -pubout -out rsa_key.pub`. Pegar la pública (una línea, sin cabeceras) en
   el `ALTER USER DBT SET RSA_PUBLIC_KEY` de `00_roles_and_users.sql`.
3. Ejecutar `00`, `01` y `02` en ese orden en una hoja de Snowsight (o `snow sql -f`). El `PUT` de `02` solo
   funciona desde un cliente (SnowSQL / `snow` CLI), no desde la hoja web; las líneas `PUT` van comentadas.
4. Exportar las variables y probar la conexión de dbt:
   ```bash
   export IIF_DBT_TARGET=snowflake SNOWFLAKE_ACCOUNT=<org>-<cuenta> SNOWFLAKE_USER=DBT \
          SNOWFLAKE_PRIVATE_KEY_PATH=/ruta/segura/rsa_key.p8
   # opcionales (valores por defecto): SNOWFLAKE_ROLE=TRANSFORMER SNOWFLAKE_WAREHOUSE=WH_IIF_XS SNOWFLAKE_DATABASE=IIF
   uv run dbt debug --profiles-dir dbt --project-dir dbt
   uv run dbt build --profiles-dir dbt --project-dir dbt
   ```
   En CI la clave va como secreto `SNOWFLAKE_PRIVATE_KEY` (contenido del `.p8`) en vez de la ruta.
5. `03` se ejecuta cada vez que se archiva una revisión del DANE; `04` cuando existan los hechos de la fase 2.

## Qué no vive en Snowflake

Los Parquet crudos y las semillas están en el repositorio; `dbt/models` es la única definición de las
transformaciones. Si la cuenta desaparece, `make dbt-build` reconstruye todo en `db/iif.duckdb` en minutos.
