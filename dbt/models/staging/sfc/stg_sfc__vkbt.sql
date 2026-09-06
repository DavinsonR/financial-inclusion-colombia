{{ config(materialized='view') }}

-- Puntos de atención por canal, entidad y municipio (mensual, 2023-01 en adelante). Trae DIVIPOLA.
-- `cantidad_puntos_antecion_activos` conserva la errata de la fuente en el nombre original; aquí se renombra.

select
    cast(fecha_corte as date)                           as fecha_corte,
    {{ periodo_id('cast(fecha_corte as date)', 'M') }}  as periodo_id,
    lpad(cast(codigo_departamento as varchar), 2, '0')  as dpto_ccdgo,
    lpad(cast(codigo_municipio as varchar), 5, '0')     as mpio_ccdgo,
    cast(codigo_canal as integer)                       as codigo_canal,
    cast(unidad_captura as integer)                     as unidad_captura,
    nombre_unidad_captura,
    cast(tipo_entidad as integer)                       as tipo_entidad,
    cast(codigo_entidad as integer)                     as codigo_entidad,
    nombre_entidad,
    cast(cantidad_puntos_atencion as bigint)            as puntos_atencion,
    cast(cantidad_puntos_antecion_activos as bigint)    as puntos_atencion_activos,
    pull_id
from {{ source('sfc', 'sfc_vkbt_desu') }}
