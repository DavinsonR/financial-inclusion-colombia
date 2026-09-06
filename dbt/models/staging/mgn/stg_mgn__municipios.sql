{{ config(materialized='view') }}

-- `mpio_ccdgo` ya es el DIVIPOLA de 5 dígitos (`iif parse mgn` lo toma de MPIO_CDPMP, B-027).

select
    mpio_ccdgo,
    dpto_ccdgo,
    mpio_cnmbr                          as nombre_mgn,
    mpio_tipo                           as mpio_tipo_raw,
    case mpio_tipo
        when 'MUNICIPIO' then 'M'
        when 'ÁREA NO MUNICIPALIZADA' then 'ANM'
        when 'ISLA' then 'ISLA'
        else mpio_tipo
    end                                 as mpio_tipo,
    cast(mpio_narea as double)          as area_km2,
    cast(mpio_nano as integer)          as anio_mgn
from {{ source('mgn', 'municipios') }}
