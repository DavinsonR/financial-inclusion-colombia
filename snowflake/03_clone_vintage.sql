-- 03_clone_vintage.sql — vintages sin copiar datos: clon zero-copy + Time Travel.
-- Ejecutar como TRANSFORMER (dueño de MARTS, con CREATE SCHEMA en IIF) cada vez que se archiva una revisión
-- oficial (p. ej. la revisión anual del DANE de julio). Idempotente por el IF NOT EXISTS.
-- Sin probar contra una cuenta real hasta que existan credenciales (ver README.md).
--
-- Motivo: el DANE revisa toda la serie de PIB cada julio. Los hechos son bitemporales (pull_id, is_current),
-- pero un clon del esquema completo congela además las dimensiones y los marts de análisis exactamente
-- como se usaron en un documento. El clon no copia micro-particiones: cuesta almacenamiento solo cuando
-- el original cambia.

USE ROLE TRANSFORMER;
USE WAREHOUSE WH_IIF_XS;

-- 1) Clon del esquema MARTS con el nombre del vintage (año_mes de la revisión que incorpora).
CREATE SCHEMA IF NOT EXISTS IIF.MARTS_V2026_07 CLONE IIF.MARTS
    COMMENT = 'Vintage 2026-07: PIB departamental 2005-2025pr (revisión DANE de julio de 2026)';

-- Variante: clonar tal como estaba MARTS en un instante, no ahora.
-- CREATE SCHEMA IF NOT EXISTS IIF.MARTS_V2026_07 CLONE IIF.MARTS
--     AT (TIMESTAMP => '2026-07-15 00:00:00'::TIMESTAMP_LTZ);

-- 2) Time Travel sobre una tabla viva (dentro de DATA_RETENTION_TIME_IN_DAYS: 1 día en Standard).
SELECT dpto_ccdgo, anio, pib_cop_millones, estado_dato
FROM IIF.MARTS.FCT_PIB_DEPARTAMENTO_ANUAL
    AT (TIMESTAMP => '2026-07-15 00:00:00'::TIMESTAMP_LTZ)
WHERE dpto_ccdgo = '11'
ORDER BY anio;

-- Por desplazamiento (hace 12 horas) o por consulta (antes de un dbt run concreto):
-- ... AT (OFFSET => -60*60*12)
-- ... BEFORE (STATEMENT => '<query_id del dbt run>')

-- 3) Diferencia entre vintages: qué cambió la revisión.
SELECT COALESCE(n.dpto_ccdgo, v.dpto_ccdgo) AS dpto_ccdgo,
       COALESCE(n.anio, v.anio)             AS anio,
       v.pib_cop_millones                   AS pib_vintage_2026_07,
       n.pib_cop_millones                   AS pib_actual,
       n.pib_cop_millones - v.pib_cop_millones AS diferencia
FROM IIF.MARTS.FCT_PIB_DEPARTAMENTO_ANUAL n
FULL OUTER JOIN IIF.MARTS_V2026_07.FCT_PIB_DEPARTAMENTO_ANUAL v
    ON n.dpto_ccdgo = v.dpto_ccdgo AND n.anio = v.anio
WHERE n.pib_cop_millones IS DISTINCT FROM v.pib_cop_millones
ORDER BY 1, 2;

-- 4) Los clones se listan y se sueltan como cualquier esquema; el READER puede leerlos si se le da USAGE + SELECT.
-- SHOW SCHEMAS LIKE 'MARTS_V%' IN DATABASE IIF;
-- GRANT USAGE ON SCHEMA IIF.MARTS_V2026_07 TO ROLE READER;
-- GRANT SELECT ON ALL TABLES IN SCHEMA IIF.MARTS_V2026_07 TO ROLE READER;
-- DROP SCHEMA IF EXISTS IIF.MARTS_V2026_07;   -- recuperable con UNDROP durante la retención
