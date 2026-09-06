-- 03_cost_controls.sql — control de coste. En el sandbox no puede haber factura, pero estas cuotas son la
-- práctica correcta en cualquier proyecto con facturación y son parte de lo que el proyecto demuestra.

-- 1. Tope de bytes que una sola consulta puede escanear (se aplica en el cliente, por sesión):
--      bq query --maximum_bytes_billed=1000000000 --use_legacy_sql=false 'SELECT ...'
--    En dbt va en profiles.yml como `maximum_bytes_billed`, ya configurado en 1 GB.

-- 2. Cuota diaria por usuario y por proyecto: se fija en la consola
--    (IAM y administración → Cuotas → BigQuery API → "Query usage per day"). No hay DDL para esto.

-- 3. Gasto real de consulta del último mes, por día y por usuario.
SELECT
    DATE(creation_time)                                        AS dia,
    user_email,
    COUNT(*)                                                   AS consultas,
    ROUND(SUM(total_bytes_billed) / POW(1024, 4), 4)           AS tib_facturados,
    ROUND(SUM(total_bytes_billed) / POW(1024, 4) * 6.25, 2)    AS usd_estimados  -- 6,25 USD por TiB bajo demanda
FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  AND job_type = 'QUERY'
  AND state = 'DONE'
GROUP BY 1, 2
ORDER BY 1 DESC;

-- 4. Almacenamiento por dataset (el sandbox permite 10 GB activos).
SELECT
    table_schema,
    ROUND(SUM(total_logical_bytes) / POW(1024, 3), 3) AS gib
FROM `region-us`.INFORMATION_SCHEMA.TABLE_STORAGE
GROUP BY 1
ORDER BY gib DESC;
