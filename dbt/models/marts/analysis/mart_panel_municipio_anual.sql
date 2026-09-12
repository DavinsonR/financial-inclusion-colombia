-- Panel analítico municipal anual, 2018 a 2024: una fila por municipio y año.
-- El límite superior es 2024 porque el valor agregado municipal del DANE llega hasta 2024p.
-- Recordatorio que no se debe perder de vista: ese valor agregado es una distribución del PIB
-- departamental, no una medición municipal (ADR-001); el crecimiento que se calcula aquí hereda esa
-- limitación y así se presenta.

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
        mpio_ccdgo,
        anio,
        {% for v in variables %}
        max(case when variable_id = '{{ v }}' then valor_anual end) as {{ v }}{{ "," if not loop.last }}
        {% endfor %}
    from {{ ref('fct_inclusion_municipio_anual') }}
    group by 1, 2

),

actividad as (

    -- Igual que en el panel departamental: el valor agregado rezagado se calcula sobre la serie completa
    -- (2011 en adelante) y no sobre el panel recortado, para que 2018 tenga denominador (ADR-017).
    select
        *,
        lag(va_corriente_mm) over (partition by mpio_ccdgo order by anio) as va_corriente_mm_rezago
    from {{ ref('fct_actividad_municipio_anual') }}

),

base as (

    select
        m.mpio_ccdgo,
        m.dpto_ccdgo,
        m.municipio,
        m.mpio_tipo,
        a.anio,
        cast(a.anio as varchar)                 as periodo_id,
        a.estado_dato,
        a.va_corriente_mm,
        a.va_corriente_mm_rezago,
        a.va_per_capita_corriente,
        a.peso_relativo_pct,
        a.poblacion_total,
        a.tasa_urbanizacion,
        e.cobertura_neta,
        e.desercion,
        i.accesos_q4                            as accesos_internet_q4,
        {% for v in variables %}
        inc.{{ v }}{{ "," if not loop.last }}
        {% endfor %}
    from actividad as a
    join {{ ref('dim_municipio') }} as m on m.mpio_ccdgo = a.mpio_ccdgo
    left join inclusion as inc on inc.mpio_ccdgo = a.mpio_ccdgo and inc.anio = a.anio
    left join {{ ref('fct_educacion_municipio_anual') }} as e on e.mpio_ccdgo = a.mpio_ccdgo and e.anio = a.anio
    left join {{ ref('fct_internet_municipio_anual') }}  as i on i.mpio_ccdgo = a.mpio_ccdgo and i.anio = a.anio
    where a.anio between 2018 and 2024

)

select
    b.*,
    lag(b.va_per_capita_corriente) over (partition by b.mpio_ccdgo order by b.anio) as va_per_capita_rezago,
    case when lag(b.va_per_capita_corriente) over (partition by b.mpio_ccdgo order by b.anio) > 0
         then ln(b.va_per_capita_corriente)
              - ln(lag(b.va_per_capita_corriente) over (partition by b.mpio_ccdgo order by b.anio))
    end                                                                             as crecimiento_va_pc_nominal
from base as b
