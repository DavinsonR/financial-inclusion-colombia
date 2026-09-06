-- 02_partitioning_clustering.sql — particionado y agrupación de las tablas grandes.
-- En BigQuery no hay índices: se reduce el escaneo con PARTITION BY (una columna de fecha o entero) y se
-- ordena físicamente con CLUSTER BY. Es lo que baja el coste por consulta y lo que mantiene el proyecto
-- dentro del terabyte gratuito al mes.
--
-- Nota del sandbox (sin facturación): toda tabla y partición expira a los 60 días. Se recrea con
-- `bash bigquery/01_load_parquet.sh` y este script.

-- Inclusión financiera vigente: 1,7 M de filas, 20 trimestres. Se consulta casi siempre por corte y
-- por departamento (unicap), así que se particiona por trimestre y se agrupa por unidad y bloque.
CREATE OR REPLACE TABLE `raw.sfc_kx2f_xjdq_part`
PARTITION BY DATE_TRUNC(fecha_corte, QUARTER)
CLUSTER BY unicap, tipo AS
SELECT * FROM `raw.sfc_kx2f_xjdq`;

CREATE OR REPLACE TABLE `raw.sfc_ptgf_ywrb_part`
PARTITION BY DATE_TRUNC(fechacorte, QUARTER)
CLUSTER BY unicap, tipo AS
SELECT * FROM `raw.sfc_ptgf_ywrb`;

-- Puntos de atención: mensual desde 2023, 1,7 M de filas; se consulta por mes y municipio.
CREATE OR REPLACE TABLE `raw.sfc_vkbt_desu_part`
PARTITION BY DATE_TRUNC(fecha_corte, MONTH)
CLUSTER BY codigo_departamento, codigo_canal AS
SELECT * FROM `raw.sfc_vkbt_desu`;

-- Internet fijo: 2,8 M de filas sin columna de fecha (año y trimestre por separado).
-- Se particiona por rango entero sobre el año, que es como se filtra.
CREATE OR REPLACE TABLE `raw.mintic_n48w_gutb_part`
PARTITION BY RANGE_BUCKET(CAST(anno AS INT64), GENERATE_ARRAY(2016, 2031, 1))
CLUSTER BY cod_departamento, cod_municipio AS
SELECT * FROM `raw.mintic_n48w_gutb`;

-- Comprobación: bytes que escanearía una consulta típica antes y después de particionar.
-- Ejecutar con `bq query --dry_run` para ver la estimación sin gastar cuota.
--   SELECT COUNT(*) FROM `raw.sfc_kx2f_xjdq`      WHERE fecha_corte = '2025-12-31';
--   SELECT COUNT(*) FROM `raw.sfc_kx2f_xjdq_part` WHERE fecha_corte = '2025-12-31';
