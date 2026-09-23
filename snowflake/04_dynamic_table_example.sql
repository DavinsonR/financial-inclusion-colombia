-- 04_dynamic_table_example.sql — una dynamic table como alternativa a un modelo dbt programado.
-- Ejecutar como TRANSFORMER una vez existan IIF.MARTS.FCT_INCLUSION_DEPARTAMENTO_TRIMESTRE e IIF.SEEDS.DIM_VARIABLE
-- (tras `dbt build --target snowflake`). Idempotente por el IF NOT EXISTS.
-- Sin probar contra una cuenta real hasta que existan credenciales (ver README.md).
--
-- Qué demuestra: Snowflake mantiene el agregado anual por sí mismo, con un retraso máximo (TARGET_LAG) de un
-- día respecto a los hechos trimestrales, refrescando de forma incremental cuando puede. Aplica la regla de
-- anualización de dim_variable exactamente como fct_inclusion_departamento_anual en dbt (ADR-001):
-- flujos = suma de los cuatro trimestres, y solo con los cuatro; stocks = valor del cuarto trimestre (un stock
-- no exige los cuatro). No hay regla 'mean': dim_variable solo admite 'sum' y 'last'.
-- dim_variable es una semilla y vive en IIF.SEEDS, no en MARTS. Los hechos aún no llevan pull_id ni
-- is_current (ADR-002 pendiente): cuando los lleven, se añade el filtro `WHERE f.is_current`.
-- Aquí vive en la base para que Power BI la lea sin depender de un `dbt run`.

USE ROLE TRANSFORMER;
USE WAREHOUSE WH_IIF_XS;

CREATE DYNAMIC TABLE IF NOT EXISTS IIF.MARTS.DT_INCLUSION_DEPARTAMENTO_ANUAL
    TARGET_LAG   = '1 day'
    WAREHOUSE    = WH_IIF_XS
    REFRESH_MODE = AUTO          -- incremental cuando la consulta lo permite, completo si no
    INITIALIZE   = ON_CREATE
    COMMENT      = 'Agregado anual de los hechos trimestrales SFC por departamento y variable (regla de dim_variable)'
AS
SELECT
    f.dpto_ccdgo,
    f.anio,
    f.variable_id,
    v.regla_anualizacion,
    CASE
        WHEN v.regla_anualizacion = 'sum' AND COUNT(DISTINCT f.trimestre) = 4 THEN SUM(f.valor)
        WHEN v.regla_anualizacion = 'last' THEN MAX(CASE WHEN f.trimestre = 4 THEN f.valor END)
    END                                   AS valor_anual,   -- nulo si la regla no se puede aplicar
    COUNT(DISTINCT f.trimestre)           AS trimestres_observados
FROM IIF.MARTS.FCT_INCLUSION_DEPARTAMENTO_TRIMESTRE f
JOIN IIF.SEEDS.DIM_VARIABLE v ON v.variable_id = f.variable_id
GROUP BY f.dpto_ccdgo, f.anio, f.variable_id, v.regla_anualizacion;

-- Operación:
--   SHOW DYNAMIC TABLES IN SCHEMA IIF.MARTS;
--   SELECT * FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY(NAME => 'IIF.MARTS.DT_INCLUSION_DEPARTAMENTO_ANUAL'));
--   ALTER DYNAMIC TABLE IIF.MARTS.DT_INCLUSION_DEPARTAMENTO_ANUAL REFRESH;    -- forzar
--   ALTER DYNAMIC TABLE IIF.MARTS.DT_INCLUSION_DEPARTAMENTO_ANUAL SUSPEND;    -- detener el gasto
