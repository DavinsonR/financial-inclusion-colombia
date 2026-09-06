{{ config(materialized='view') }}

-- Vista sobre el panel legado congelado (462 filas = 33 departamentos × 14 trimestres, 2017Q4-2021Q1).
-- Expone solo las 21 columnas que el notebook original consume (USED_RAW_COLUMNS en
-- src/iif/legacy/constants.py), renombradas a snake_case y tipadas, más `periodo_id` para
-- enlazar con dim_periodo. `fecha` es el primer día del último mes del trimestre (p. ej. 2017-12-01).
-- No corrige nada: los ceros de internet y las series anuales repetidas por trimestre se quedan tal cual;
-- las correcciones viven en los modelos analíticos, no aquí.

with fuente as (

    select * from {{ read_parquet_path(var('legacy_panel_parquet')) }}

)

select
    cast("Depto Base"                    as varchar)          as departamento,
    cast("Año"                           as integer)          as anio,
    cast("Fecha"                         as date)             as fecha,
    {{ periodo_id('cast("Fecha" as date)', 'Q') }}            as periodo_id,

    -- SFC: acceso y uso (corresponsales y transacciones), cuentas y crédito
    cast("NRO CORRESPONSALES ACTIVOS"    as bigint)           as nro_corresp_activos,
    cast("NRO DEPOSITOS"                 as bigint)           as nro_depositos,
    cast("NRO PAGOS"                     as bigint)           as nro_pagos,
    cast("NRO TRANSFERENCIAS"            as bigint)           as nro_transf,
    cast("NRO TOTAL "                    as bigint)           as nro_total,   -- el nombre trae espacio final en el parquet
    cast("NRO TOTAL CTA AHORROS"         as bigint)           as nro_total_cta_ah,
    cast("MONTO TOTAL CREDITO CONSUMO"   as double)           as monto_total_cred_cons,
    cast("MONTO TOTAL CREDITO VIVIENDA"  as double)           as monto_total_cred_viv,
    cast("MONTO TOTAL MICROCREDITO"      as double)           as monto_total_micro,

    -- Controles anuales repetidos por trimestre (DANE, MinTIC)
    cast("Poblacion"                     as double)           as poblacion,
    cast("Conexión a internet %"         as double)           as internet_pct,
    cast("Años promedio de educación"    as double)           as educacion_anios,
    cast("IPC %"                         as double)           as ipc_pct,
    cast("Empleo Formal"                 as double)           as empleo_formal,
    cast("Empleo Informal"               as double)           as empleo_informal,
    cast("Densidad Poblacional"          as double)           as densidad_poblacional,
    cast("PIB Percapita"                 as double)           as pib_percapita,
    cast("PIB Crecimiento"               as double)           as pib_crecimiento

from fuente
