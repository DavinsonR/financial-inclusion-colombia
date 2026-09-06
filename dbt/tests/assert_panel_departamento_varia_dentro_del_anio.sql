-- R-05, la regla que existe por el defecto que originó este proyecto: la dependiente del panel debe variar
-- de verdad entre periodos. Falla si el crecimiento del PIB real per cápita es exactamente cero en más del
-- 5 % de las filas, que es la firma de un valor anual repetido.
with base as (
    select count(*) as filas,
           sum(case when crecimiento_pib_real_pc = 0 then 1 else 0 end) as ceros_exactos
    from {{ ref('mart_panel_departamento_anual') }}
    where crecimiento_pib_real_pc is not null
)
select * from base where ceros_exactos > 0.05 * filas
