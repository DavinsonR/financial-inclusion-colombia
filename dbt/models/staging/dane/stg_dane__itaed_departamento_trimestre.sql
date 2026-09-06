{{ config(materialized='view') }}

-- Vista tipada sobre data/interim/dane/itaed_departamento_trimestre.parquet (`iif parse dane`). Sin transformación de valores.

select dpto_ccdgo, departamento, cast(anio as integer) as anio, cast(trimestre as integer) as trimestre, cast(anio as varchar) || 'Q' || cast(trimestre as varchar) as periodo_id, estado_dato, indice_original
from {{ source('dane', 'itaed_departamento_trimestre') }}
