{{ config(materialized='view') }}

select
    dpto_ccdgo,
    dpto_cnmbr                          as nombre_mgn,
    cast(dpto_narea as double)          as area_km2,
    cast(dpto_nano as integer)          as anio_mgn
from {{ source('mgn', 'departamentos') }}
