{{ config(materialized='view') }}

-- Vista tipada sobre data/interim/dane/poblacion_departamento_anual.parquet (`iif parse dane`). Sin transformación de valores.

select dpto_ccdgo, departamento, cast(anio as integer) as anio, cast(anio as varchar) as periodo_id, area, cast(poblacion as bigint) as poblacion, fuente
from {{ source('dane', 'poblacion_departamento_anual') }}
