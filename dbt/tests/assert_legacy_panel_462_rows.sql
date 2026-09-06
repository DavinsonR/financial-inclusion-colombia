-- El panel legado congelado tiene exactamente 462 filas (33 departamentos × 14 trimestres).
-- Falla (devuelve una fila) si el conteo cambia: significaría que el parquet ya no es el original.
select count(*) as n_filas
from {{ ref('stg_legacy__panel_trimestral') }}
having count(*) <> 462
