-- Panel analítico departamental anual, 2018 a 2025: una fila por departamento y año, con las variables de
-- inclusión financiera en columnas, la actividad económica del DANE y los controles.
-- 2017 queda fuera porque solo tiene el cuarto trimestre y ningún flujo se puede anualizar (ADR-001).
--
-- El crecimiento se calcula sobre el PIB real per cápita (constante 2015 dividido por población total),
-- que es una serie anual verdadera: aquí ningún valor anual se repite dentro del año (R-05).

{{ config(materialized='table') }}
-- depends_on: {{ ref('dim_variable') }}

{% set variables = [] %}
{% if execute %}
    {% set variables = run_query(
        "select variable_id from " ~ ref('dim_variable') ~
        " where disponible_en = 'ambas' and dimension_iif <> 'ninguna' order by 1"
    ).columns[0].values() %}
{% endif %}

with inclusion as (

    select
        dpto_ccdgo,
        anio,
        {% for v in variables %}
        max(case when variable_id = '{{ v }}' then valor_anual end) as {{ v }}{{ "," if not loop.last }}
        {% endfor %}
    from {{ ref('fct_inclusion_departamento_anual') }}
    group by 1, 2

),

actividad as (

    select * from {{ ref('fct_actividad_departamento_anual') }}

),

itaed as (

    select dpto_ccdgo, anio, avg(indice_original) as itaed_promedio_anual, count(*) as itaed_trimestres
    from {{ ref('stg_dane__itaed_departamento_trimestre') }}
    where dpto_ccdgo not in ('00', 'RESTO')
    group by 1, 2

),

educacion as (

    select dpto_ccdgo, anio,
           sum(poblacion_5_16)                                             as poblacion_5_16,
           sum(cobertura_neta * poblacion_5_16) / nullif(sum(case when cobertura_neta is not null then poblacion_5_16 end), 0) as cobertura_neta_ponderada
    from {{ ref('fct_educacion_municipio_anual') }}
    group by 1, 2

),

internet as (

    select dpto_ccdgo, anio, sum(accesos_q4) as accesos_internet_q4
    from {{ ref('fct_internet_municipio_anual') }}
    group by 1, 2

),

base as (

    select
        d.dpto_ccdgo,
        d.departamento,
        d.region,
        a.anio,
        cast(a.anio as varchar)                     as periodo_id,
        a.estado_dato,
        a.pib_corriente_mm,
        a.pib_constante_2015_mm,
        a.pib_real_per_capita,
        a.poblacion_total,
        a.tasa_urbanizacion,
        it.itaed_promedio_anual,
        it.itaed_trimestres,
        e.poblacion_5_16,
        e.cobertura_neta_ponderada,
        i.accesos_internet_q4,
        {% for v in variables %}
        inc.{{ v }}{{ "," if not loop.last }}
        {% endfor %}
    from actividad as a
    join {{ ref('dim_departamento') }} as d on d.dpto_ccdgo = a.dpto_ccdgo
    left join inclusion as inc on inc.dpto_ccdgo = a.dpto_ccdgo and inc.anio = a.anio
    left join itaed     as it  on it.dpto_ccdgo  = a.dpto_ccdgo and it.anio  = a.anio
    left join educacion as e   on e.dpto_ccdgo   = a.dpto_ccdgo and e.anio   = a.anio
    left join internet  as i   on i.dpto_ccdgo   = a.dpto_ccdgo and i.anio   = a.anio
    where a.anio between 2018 and 2025

)

select
    b.*,
    lag(b.pib_real_per_capita) over (partition by b.dpto_ccdgo order by b.anio)   as pib_real_per_capita_rezago,
    case when lag(b.pib_real_per_capita) over (partition by b.dpto_ccdgo order by b.anio) > 0
         then ln(b.pib_real_per_capita)
              - ln(lag(b.pib_real_per_capita) over (partition by b.dpto_ccdgo order by b.anio))
    end                                                                           as crecimiento_pib_real_pc
from base as b
