-- Accesos fijos a internet por municipio y año (MinTIC, 2016 a 2023Q3). Es un stock al corte del trimestre,
-- así que el valor anual es el del cuarto trimestre; 2023 solo llega al tercero y por eso queda nulo.
-- La fuente se abandonó en 2024: la serie no continúa (ADR-004, internet fuera del índice).

with por_trimestre as (

    select
        mpio_ccdgo,
        dpto_ccdgo,
        anio,
        trimestre,
        sum(accesos) as accesos
    from {{ ref('stg_mintic__internet') }}
    group by 1, 2, 3, 4

)

select
    mpio_ccdgo,
    dpto_ccdgo,
    anio,
    cast(anio as varchar)                        as periodo_id,
    count(distinct trimestre)                    as trimestres_observados,
    max(trimestre)                               as ultimo_trimestre,
    max(case when trimestre = 4 then accesos end) as accesos_q4,
    max(accesos)                                 as accesos_max_trimestre
from por_trimestre
group by 1, 2, 3
