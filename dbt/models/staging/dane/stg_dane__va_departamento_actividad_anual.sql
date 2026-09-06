{{ config(materialized='view') }}

-- Vista tipada sobre data/interim/dane/va_departamento_actividad_anual.parquet (`iif parse dane`). Sin transformación de valores.

select dpto_ccdgo, departamento, cuenta, seccion_ciiu, actividad, cast(anio as integer) as anio, cast(anio as varchar) as periodo_id, estado_dato, va_corriente_mm, va_constante_2015_mm
from {{ source('dane', 'va_departamento_actividad_anual') }}
