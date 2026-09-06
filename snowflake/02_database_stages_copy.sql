-- 02_database_stages_copy.sql — base IIF, esquemas, formato Parquet, stage interno, COPY INTO y tabla VARIANT.
-- Ejecutar como SYSADMIN después de 00 y 01. Idempotente salvo donde se indica (COPY INTO carga lo que
-- encuentre en el stage que no haya cargado ya: Snowflake recuerda los archivos ya copiados 64 días).
-- Sin probar contra una cuenta real hasta que existan credenciales (ver README.md).
--
-- Esquemas (mismos nombres que en DuckDB gracias a la macro generate_schema_name de dbt):
--   RAW           Parquet copiados tal cual desde data/raw + filas crudas de la API en VARIANT (rol LOADER)
--   STAGING, INTERMEDIATE, SEEDS, MARTS   los crea y escribe dbt (rol TRANSFORMER)

USE ROLE SYSADMIN;

CREATE DATABASE IF NOT EXISTS IIF
    DATA_RETENTION_TIME_IN_DAYS = 1    -- Time Travel; Standard permite máximo 1 día, Enterprise hasta 90
    COMMENT = 'Inclusión financiera y crecimiento regional en Colombia (proyecto iif)';

CREATE SCHEMA IF NOT EXISTS IIF.RAW          COMMENT = 'Cargas crudas: Parquet del repo y JSON de la API';
CREATE SCHEMA IF NOT EXISTS IIF.STAGING      COMMENT = 'dbt: vistas de limpieza y tipado';
CREATE SCHEMA IF NOT EXISTS IIF.INTERMEDIATE COMMENT = 'dbt: empalmes, unpivot y crosswalks aplicados';
CREATE SCHEMA IF NOT EXISTS IIF.SEEDS        COMMENT = 'dbt: semillas (crosswalks y dimensiones pequeñas)';
CREATE SCHEMA IF NOT EXISTS IIF.MARTS        COMMENT = 'dbt: dimensiones, hechos y marts de análisis';

------------------------------------------------------------------------------------------------------
-- Formato y stage interno para Parquet
------------------------------------------------------------------------------------------------------
CREATE FILE FORMAT IF NOT EXISTS IIF.RAW.FF_PARQUET
    TYPE = PARQUET
    COMPRESSION = AUTO
    USE_LOGICAL_TYPE = TRUE            -- fechas y timestamps lógicos de Parquet como DATE/TIMESTAMP
    COMMENT = 'Parquet escritos por pyarrow desde iif acquire';

CREATE STAGE IF NOT EXISTS IIF.RAW.STG_PARQUET
    FILE_FORMAT = IIF.RAW.FF_PARQUET
    DIRECTORY = (ENABLE = TRUE)        -- permite LIST y consultas de metadatos del stage
    COMMENT = 'Stage interno; la ruta replica data/raw/<fuente>/<dataset>/';

-- Subida (PUT solo funciona desde un cliente, no desde la hoja web): con SnowSQL o `snow sql`
--   PUT file:///ruta/al/repo/data/raw/sfc/kx2f_xjdq/*.parquet @IIF.RAW.STG_PARQUET/sfc/kx2f_xjdq/
--       AUTO_COMPRESS = FALSE OVERWRITE = FALSE;
--   LIST @IIF.RAW.STG_PARQUET/sfc/kx2f_xjdq/;

------------------------------------------------------------------------------------------------------
-- Tabla RAW por dataset: esquema inferido del propio Parquet (una vez) y carga por nombre de columna
------------------------------------------------------------------------------------------------------
-- Ejemplo con SFC kx2f-xjdq. Repetir el patrón para sfc/ptgf_ywrb, sfc/vkbt_desu, mintic/n48w_gutb,
-- men/nudc_7mev y los Parquet de data/interim (dane/*, mgn/*).
CREATE TABLE IF NOT EXISTS IIF.RAW.SFC_KX2F_XJDQ
    USING TEMPLATE (
        SELECT ARRAY_AGG(OBJECT_CONSTRUCT(*))
        FROM TABLE(INFER_SCHEMA(
            LOCATION    => '@IIF.RAW.STG_PARQUET/sfc/kx2f_xjdq/',
            FILE_FORMAT => 'IIF.RAW.FF_PARQUET'
        ))
    )
    COMMENT = 'SFC kx2f-xjdq tal cual (una fila por entidad × unidad × renglón × trimestre × pull)';

COPY INTO IIF.RAW.SFC_KX2F_XJDQ
    FROM @IIF.RAW.STG_PARQUET/sfc/kx2f_xjdq/
    FILE_FORMAT = (FORMAT_NAME = 'IIF.RAW.FF_PARQUET')
    MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE   -- casa columnas por nombre, no por posición
    ON_ERROR = ABORT_STATEMENT;               -- un Parquet corrupto detiene toda la carga

-- Recarga completa de un dataset (p. ej. tras cambiar la partición): TRUNCATE + COPY INTO ... FORCE = TRUE.

------------------------------------------------------------------------------------------------------
-- Filas crudas de la API en VARIANT: conserva el JSON exacto de cada descarga (pull_id) y se aplana con FLATTEN
------------------------------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS IIF.RAW.SFC_VARIANT (
    payload   VARIANT        NOT NULL COMMENT 'Un registro JSON de la API SODA tal cual llegó',
    pull_id   STRING         NOT NULL COMMENT 'Identificador de la descarga (dim_vintage.pull_id)',
    loaded_at TIMESTAMP_NTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
COMMENT = 'Respaldo crudo de la API SFC; permite reconstruir cualquier columna aunque cambie el esquema del Parquet';

CREATE STAGE IF NOT EXISTS IIF.RAW.STG_JSON
    FILE_FORMAT = (TYPE = JSON STRIP_OUTER_ARRAY = TRUE COMPRESSION = AUTO)
    COMMENT = 'JSON (gz) crudos de la API SODA';

-- PUT file:///ruta/al/repo/data/raw/sfc/kx2f_xjdq/_json/kx2f_xjdq_2026-09-06.json.gz @IIF.RAW.STG_JSON/sfc/kx2f_xjdq/;
COPY INTO IIF.RAW.SFC_VARIANT (payload, pull_id)
    FROM (
        SELECT $1, REGEXP_SUBSTR(METADATA$FILENAME, '[^/]+(?=\\.json)')   -- pull_id = nombre del archivo
        FROM @IIF.RAW.STG_JSON/sfc/kx2f_xjdq/
    )
    ON_ERROR = ABORT_STATEMENT;

-- Vista larga: una fila por (registro, columna). Las claves conocidas se tipan; el resto queda como par clave/valor.
CREATE VIEW IF NOT EXISTS IIF.RAW.V_SFC_VARIANT_LARGO AS
SELECT
    v.pull_id,
    v.loaded_at,
    v.payload:unicap::INTEGER       AS unicap,
    v.payload:descrip_uc::STRING    AS descrip_uc,
    v.payload:tipo::STRING          AS tipo,
    f.key                           AS columna,
    f.value::STRING                 AS valor
FROM IIF.RAW.SFC_VARIANT v,
     LATERAL FLATTEN(INPUT => v.payload) f
WHERE f.key NOT IN ('unicap', 'descrip_uc', 'tipo');

------------------------------------------------------------------------------------------------------
-- Permisos
------------------------------------------------------------------------------------------------------
GRANT USAGE ON DATABASE IIF TO ROLE LOADER;
GRANT USAGE ON DATABASE IIF TO ROLE TRANSFORMER;
GRANT USAGE ON DATABASE IIF TO ROLE READER;

-- LOADER: dueño operativo de RAW (tablas, stages, COPY INTO).
GRANT ALL PRIVILEGES ON SCHEMA IIF.RAW TO ROLE LOADER;
GRANT ALL PRIVILEGES ON ALL TABLES    IN SCHEMA IIF.RAW TO ROLE LOADER;
GRANT ALL PRIVILEGES ON FUTURE TABLES IN SCHEMA IIF.RAW TO ROLE LOADER;
GRANT ALL PRIVILEGES ON ALL STAGES    IN SCHEMA IIF.RAW TO ROLE LOADER;
GRANT ALL PRIVILEGES ON FUTURE STAGES IN SCHEMA IIF.RAW TO ROLE LOADER;
GRANT USAGE ON ALL FILE FORMATS IN SCHEMA IIF.RAW TO ROLE LOADER;

-- TRANSFORMER (dbt): lee RAW, crea esquemas si hacen falta y es dueño de STAGING/INTERMEDIATE/SEEDS/MARTS.
GRANT USAGE  ON SCHEMA IIF.RAW TO ROLE TRANSFORMER;
GRANT SELECT ON ALL TABLES    IN SCHEMA IIF.RAW TO ROLE TRANSFORMER;
GRANT SELECT ON FUTURE TABLES IN SCHEMA IIF.RAW TO ROLE TRANSFORMER;
GRANT SELECT ON ALL VIEWS     IN SCHEMA IIF.RAW TO ROLE TRANSFORMER;
GRANT SELECT ON FUTURE VIEWS  IN SCHEMA IIF.RAW TO ROLE TRANSFORMER;
GRANT READ   ON STAGE IIF.RAW.STG_PARQUET TO ROLE TRANSFORMER;   -- para leer Parquet directo del stage si hace falta
GRANT CREATE SCHEMA ON DATABASE IIF TO ROLE TRANSFORMER;         -- clones por vintage (03) y esquemas nuevos de dbt
GRANT ALL PRIVILEGES ON SCHEMA IIF.STAGING      TO ROLE TRANSFORMER;
GRANT ALL PRIVILEGES ON SCHEMA IIF.INTERMEDIATE TO ROLE TRANSFORMER;
GRANT ALL PRIVILEGES ON SCHEMA IIF.SEEDS        TO ROLE TRANSFORMER;
GRANT ALL PRIVILEGES ON SCHEMA IIF.MARTS        TO ROLE TRANSFORMER;

-- READER: solo MARTS, incluidas las tablas que dbt cree en el futuro.
GRANT USAGE  ON SCHEMA IIF.MARTS TO ROLE READER;
GRANT SELECT ON ALL TABLES    IN SCHEMA IIF.MARTS TO ROLE READER;
GRANT SELECT ON FUTURE TABLES IN SCHEMA IIF.MARTS TO ROLE READER;
GRANT SELECT ON ALL VIEWS     IN SCHEMA IIF.MARTS TO ROLE READER;
GRANT SELECT ON FUTURE VIEWS  IN SCHEMA IIF.MARTS TO ROLE READER;
GRANT SELECT ON ALL DYNAMIC TABLES    IN SCHEMA IIF.MARTS TO ROLE READER;
GRANT SELECT ON FUTURE DYNAMIC TABLES IN SCHEMA IIF.MARTS TO ROLE READER;

-- Verificación:
--   SELECT COUNT(*) FROM IIF.RAW.SFC_KX2F_XJDQ;                       -- debe igualar el conteo del manifiesto
--   SELECT pull_id, COUNT(*) FROM IIF.RAW.SFC_VARIANT GROUP BY 1;
--   SELECT * FROM IIF.RAW.V_SFC_VARIANT_LARGO LIMIT 20;
