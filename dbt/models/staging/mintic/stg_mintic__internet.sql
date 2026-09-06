{{ config(materialized='view') }}

-- Accesos fijos a internet por municipio, proveedor, segmento y tecnología (trimestral, 2016Q1 a 2023Q3).
-- Los decimales con coma ya vienen convertidos desde la descarga. La ausencia de fila es NULL, nunca cero (R-13).

select
    cast(anno as integer)                                       as anio,
    cast(trimestre as integer)                                  as trimestre,
    cast(anno as varchar) || 'Q' || cast(trimestre as varchar)  as periodo_id,
    lpad(cast(cod_departamento as varchar), 2, '0')             as dpto_ccdgo,
    lpad(cast(cod_municipio as varchar), 5, '0')                as mpio_ccdgo,
    proveedor,
    segmento,
    tecnologia,
    cast(velocidad_bajada as double)                            as velocidad_bajada_mbps,
    cast(velocidad_subida as double)                            as velocidad_subida_mbps,
    cast(no_de_accesos as bigint)                               as accesos,
    pull_id
from {{ source('mintic', 'mintic_n48w_gutb') }}
where cod_municipio is not null  -- 10 filas de 2,8 M sin código (registros de proveedor sin municipio)
