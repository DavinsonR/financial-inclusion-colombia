{{ config(materialized='view') }}

-- Vista tipada sobre data/interim/dane/va_municipio_anual.parquet (`iif parse dane`). Sin transformación de valores.

select mpio_ccdgo, municipio, dpto_ccdgo, departamento, cast(anio as integer) as anio, cast(anio as varchar) as periodo_id, estado_dato, va_corriente_mm, va_primarias_mm, va_secundarias_mm, va_terciarias_mm, va_total_cuadro_mm, peso_relativo_pct
from {{ source('dane', 'va_municipio_anual') }}
