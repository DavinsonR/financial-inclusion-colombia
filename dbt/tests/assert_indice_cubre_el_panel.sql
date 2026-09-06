-- El índice debe existir para casi todas las filas del panel departamental: si falta en más del 5 %, algo
-- se rompió entre `iif index` y el warehouse (por ejemplo, un panel reconstruido sin volver a calcularlo).
with base as (
    select count(*) as filas, sum(case when iif_compuesto is null then 1 else 0 end) as sin_indice
    from {{ ref('mart_indice_departamento_anual') }}
)
select * from base where sin_indice > 0.05 * filas
