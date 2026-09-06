-- 00_roles_and_users.sql — RBAC mínimo para el almacén IIF.
-- Ejecutar UNA vez como ACCOUNTADMIN (o USERADMIN + SECURITYADMIN). Idempotente: todo usa IF NOT EXISTS
-- y los GRANT se pueden repetir sin efecto.
-- Sin probar contra una cuenta real hasta que existan credenciales (ver README.md).
--
-- Roles (principio de mínimo privilegio, patrón loader/transformer/reader):
--   LOADER       sube Parquet/JSON al stage interno y ejecuta COPY INTO en IIF.RAW.
--   TRANSFORMER  rol de dbt: lee RAW, crea/escribe STAGING, INTERMEDIATE, SEEDS y MARTS.
--   READER       solo lectura de MARTS (Power BI, revisores).
-- Jerarquía: SYSADMIN hereda los tres para poder administrar; TRANSFORMER hereda READER.

USE ROLE USERADMIN;

CREATE ROLE IF NOT EXISTS LOADER      COMMENT = 'IIF: carga de archivos crudos al esquema RAW (stage + COPY INTO)';
CREATE ROLE IF NOT EXISTS TRANSFORMER COMMENT = 'IIF: rol de dbt; transforma RAW -> STAGING -> MARTS';
CREATE ROLE IF NOT EXISTS READER      COMMENT = 'IIF: solo lectura de MARTS';

USE ROLE SECURITYADMIN;

GRANT ROLE LOADER      TO ROLE SYSADMIN;
GRANT ROLE TRANSFORMER TO ROLE SYSADMIN;
GRANT ROLE READER      TO ROLE SYSADMIN;
GRANT ROLE READER      TO ROLE TRANSFORMER;

-- Usuario de servicio para dbt: sin contraseña, autenticación por par de claves RSA.
-- Generar el par (una vez, fuera del repositorio; el .p8 está en .gitignore):
--   openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out rsa_key.p8 -nocrypt
--   openssl rsa -in rsa_key.p8 -pubout -out rsa_key.pub
-- y pegar el contenido de rsa_key.pub (sin las líneas BEGIN/END) en el ALTER USER de abajo.
USE ROLE USERADMIN;

CREATE USER IF NOT EXISTS DBT
    LOGIN_NAME        = 'DBT'
    DISPLAY_NAME      = 'dbt (iif)'
    TYPE              = SERVICE            -- usuario de servicio: sin MFA ni contraseña
    DEFAULT_ROLE      = TRANSFORMER
    DEFAULT_WAREHOUSE = WH_IIF_XS
    DEFAULT_NAMESPACE = IIF.MARTS
    COMMENT           = 'IIF: usado por dbt-snowflake desde local y CI (SNOWFLAKE_USER=DBT)';

-- <<< REEMPLAZAR antes de ejecutar: clave pública RSA en una sola línea, sin cabeceras >>>
ALTER USER DBT SET RSA_PUBLIC_KEY = 'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA_REEMPLAZAR_CON_LA_CLAVE_PUBLICA_';
-- Rotación sin corte: ALTER USER DBT SET RSA_PUBLIC_KEY_2 = '...'; luego UNSET RSA_PUBLIC_KEY.

USE ROLE SECURITYADMIN;

GRANT ROLE TRANSFORMER TO USER DBT;
GRANT ROLE LOADER      TO USER DBT;   -- el mismo usuario sube los Parquet del repo (iif load snowflake)

-- Verificación:
--   DESC USER DBT;                        -- RSA_PUBLIC_KEY_FP debe coincidir con el fingerprint local
--   SHOW GRANTS TO USER DBT;
