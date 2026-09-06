-- Hecho ANUAL por municipio y variable, aplicando la regla de anualización de dim_variable:
--   flujo → suma de los cuatro trimestres del año, y solo si están los cuatro;
--   stock → valor del cuarto trimestre.
-- `trimestres_observados` deja ver por qué falta un año: 2017 solo tiene el cuarto trimestre y 2026 aún no
-- está completo, así que ningún flujo se publica para esos años.

with base as (

    select * from {{ ref('fct_inclusion_municipio_trimestre') }}

),

anual as (

    select
        mpio_ccdgo,
        dpto_ccdgo,
        variable_id,
        dimension_iif,
        bloque,
        unidad,
        naturaleza,
        anio,
        cast(anio as varchar)                                             as periodo_id,
        count(distinct trimestre)                                         as trimestres_observados,
        sum(valor)                                                        as suma_trimestres,
        max(case when trimestre = 4 then valor end)                       as valor_q4,
        max(fuente)                                                       as fuente_mas_reciente
    from base
    group by all

)

select
    a.*,
    case
        when v.regla_anualizacion = 'sum'  and a.trimestres_observados = 4 then a.suma_trimestres
        when v.regla_anualizacion = 'last'                                then a.valor_q4
    end                                                                   as valor_anual,
    v.regla_anualizacion
from anual as a
join {{ ref('dim_variable') }} as v on v.variable_id = a.variable_id
