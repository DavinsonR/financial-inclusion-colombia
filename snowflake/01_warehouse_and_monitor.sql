-- 01_warehouse_and_monitor.sql — cómputo mínimo y tope de gasto.
-- Ejecutar como ACCOUNTADMIN (los resource monitors solo los crea ACCOUNTADMIN). Idempotente.
-- Sin probar contra una cuenta real hasta que existan credenciales (ver README.md).
--
-- Un solo warehouse X-Small (1 crédito/hora cuando está activo), autosuspensión a los 60 s de inactividad,
-- reanudación automática y arranque suspendido. Con cargas solo cuando cambian los datos, el consumo
-- esperado es de 3-10 USD/mes; el monitor RM_IIF corta a 10 créditos mensuales.

USE ROLE ACCOUNTADMIN;

CREATE WAREHOUSE IF NOT EXISTS WH_IIF_XS
    WITH WAREHOUSE_SIZE            = 'X-SMALL'
         WAREHOUSE_TYPE            = 'STANDARD'
         AUTO_SUSPEND              = 60          -- segundos; mínimo práctico
         AUTO_RESUME               = TRUE
         INITIALLY_SUSPENDED       = TRUE
         MIN_CLUSTER_COUNT         = 1
         MAX_CLUSTER_COUNT         = 1
         STATEMENT_TIMEOUT_IN_SECONDS = 1800    -- ninguna consulta del proyecto debería pasar de 30 min
         COMMENT = 'IIF: único warehouse; dbt, cargas y lecturas de Power BI';

-- Tope mensual: aviso al 75 %, suspensión (deja terminar lo que corre) al 100 % y corte inmediato al 110 %.
CREATE RESOURCE MONITOR IF NOT EXISTS RM_IIF
    WITH CREDIT_QUOTA    = 10
         FREQUENCY       = MONTHLY
         START_TIMESTAMP = IMMEDIATELY
         NOTIFY_USERS    = ()                    -- añadir el usuario humano de la cuenta: NOTIFY_USERS = (NOMBRE)
    TRIGGERS ON  75 PERCENT DO NOTIFY
             ON 100 PERCENT DO SUSPEND
             ON 110 PERCENT DO SUSPEND_IMMEDIATE;

ALTER WAREHOUSE WH_IIF_XS SET RESOURCE_MONITOR = RM_IIF;

-- Segunda red de seguridad a nivel de cuenta (mismo monitor): descomentar si la cuenta solo sirve a este proyecto.
-- ALTER ACCOUNT SET RESOURCE_MONITOR = RM_IIF;

-- Quién puede encender el warehouse.
GRANT USAGE, OPERATE ON WAREHOUSE WH_IIF_XS TO ROLE LOADER;
GRANT USAGE, OPERATE ON WAREHOUSE WH_IIF_XS TO ROLE TRANSFORMER;
GRANT USAGE          ON WAREHOUSE WH_IIF_XS TO ROLE READER;

-- Verificación y seguimiento del gasto:
--   SHOW WAREHOUSES LIKE 'WH_IIF_XS';
--   SHOW RESOURCE MONITORS;
--   SELECT START_TIME, CREDITS_USED FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
--    WHERE WAREHOUSE_NAME = 'WH_IIF_XS' ORDER BY START_TIME DESC LIMIT 50;
