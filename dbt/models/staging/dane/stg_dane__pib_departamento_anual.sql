{{ config(materialized='view') }}

-- Vista tipada sobre data/interim/dane/pib_departamento_anual.parquet (`iif parse dane`). Sin transformación de valores.

select dpto_ccdgo, departamento, cast(anio as integer) as anio, cast(anio as varchar) as periodo_id, estado_dato, pib_corriente_mm, pib_constante_2015_mm, pib_per_capita_corriente
from {{ source('dane', 'pib_departamento_anual') }}
