-- 04_dynamic_table_example.sql — una dynamic table como alternativa a un modelo dbt programado.
-- Ejecutar como TRANSFORMER una vez existan fct_inclusion_departamento_trimestre, dim_periodo y dim_variable
-- en IIF.MARTS (fase 2). Idempotente por el IF NOT EXISTS.
-- Sin probar contra una cuenta real hasta que existan credenciales (ver README.md).
--
-- Qué demuestra: Snowflake mantiene el agregado anual por sí mismo, con un retraso máximo (TARGET_LAG) de un
-- día respecto a los hechos trimestrales, refrescando de forma incremental cuando puede. Aplica la regla de
-- anualización de dim_variable: flujos = suma de los cuatro trimestres (se exigen los cuatro), stocks = valor
-- del cuarto trimestre, medias = promedio. Es la misma lógica de fct_inclusion_departamento_anual en dbt;
-- aquí vive en la base para que Power BI la lea sin depender de un `dbt run`.

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
    p.anio,
    f.variable_id,
    v.regla_anualizacion,
    CASE v.regla_anualizacion
        WHEN 'sum'  THEN SUM(f.valor)
        WHEN 'last' THEN MAX(CASE WHEN p.trimestre = 4 THEN f.valor END)
        WHEN 'mean' THEN AVG(f.valor)
    END                                   AS valor_anual,
    COUNT(*)                              AS n_trimestres,
    MAX(f.pull_id)                        AS pull_id
FROM IIF.MARTS.FCT_INCLUSION_DEPARTAMENTO_TRIMESTRE f
JOIN IIF.MARTS.DIM_PERIODO  p ON p.periodo_id = f.periodo_id AND p.frecuencia = 'Q'
JOIN IIF.MARTS.DIM_VARIABLE v ON v.variable_id = f.variable_id
WHERE f.is_current
GROUP BY f.dpto_ccdgo, p.anio, f.variable_id, v.regla_anualizacion
HAVING COUNT(*) = 4;                      -- un año incompleto no se anualiza (no se inventan trimestres)

-- Operación:
--   SHOW DYNAMIC TABLES IN SCHEMA IIF.MARTS;
--   SELECT * FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY(NAME => 'IIF.MARTS.DT_INCLUSION_DEPARTAMENTO_ANUAL'));
--   ALTER DYNAMIC TABLE IIF.MARTS.DT_INCLUSION_DEPARTAMENTO_ANUAL REFRESH;    -- forzar
--   ALTER DYNAMIC TABLE IIF.MARTS.DT_INCLUSION_DEPARTAMENTO_ANUAL SUSPEND;    -- detener el gasto
