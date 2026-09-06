-- Dimensión de tiempo con tres frecuencias en una sola tabla (clave natural `periodo_id`):
--   A: 'YYYY'     2005-2026   (PIB, población, educación, valor agregado)
--   Q: 'YYYYQn'   2015Q1-2026Q4 (SFC ptgf/kx2f, ITAED, MinTIC)
--   M: 'YYYY-MM'  2023-01-2026-12 (SFC puntos de atención vkbt)
-- `periodo_anio_id` enlaza cada fila con su año (autorreferencia para anualizar).
-- Se genera desde una única rejilla mensual (dbt_utils.date_spine con datepart month, que existe en
-- todos los adaptadores) y se filtra; los rangos son variables del proyecto.

{% set a0 = var('periodo_anual_desde') %}
{% set a1 = var('periodo_anual_hasta') %}
{% set q0 = var('periodo_trimestral_desde') %}
{% set m0 = var('periodo_mensual_desde') %}

with meses as (

    {{ dbt_utils.date_spine(
        datepart="month",
        start_date="cast('" ~ a0 ~ "-01-01' as date)",
        end_date="cast('" ~ (a1 + 1) ~ "-01-01' as date)"
    ) }}

),

base as (

    select
        cast(date_month as date)                          as fecha_inicio,
        cast(extract(year from date_month) as integer)    as anio,
        cast(extract(quarter from date_month) as integer) as trimestre,
        cast(extract(month from date_month) as integer)   as mes
    from meses

),

anual as (

    select
        {{ periodo_id('fecha_inicio', 'A') }}             as periodo_id,
        'A'                                               as frecuencia,
        anio,
        cast(null as integer)                             as trimestre,
        cast(null as integer)                             as mes,
        fecha_inicio,
        cast({{ dbt.last_day('fecha_inicio', 'year') }} as date)    as fecha_fin
    from base
    where mes = 1

),

trimestral as (

    select
        {{ periodo_id('fecha_inicio', 'Q') }}             as periodo_id,
        'Q'                                               as frecuencia,
        anio,
        trimestre,
        cast(null as integer)                             as mes,
        fecha_inicio,
        cast({{ dbt.last_day('fecha_inicio', 'quarter') }} as date) as fecha_fin
    from base
    where mes in (1, 4, 7, 10)
      and anio >= {{ q0 }}

),

mensual as (

    select
        {{ periodo_id('fecha_inicio', 'M') }}             as periodo_id,
        'M'                                               as frecuencia,
        anio,
        trimestre,
        mes,
        fecha_inicio,
        cast({{ dbt.last_day('fecha_inicio', 'month') }} as date)   as fecha_fin
    from base
    where anio >= {{ m0 }}

),

unido as (

    select * from anual
    union all
    select * from trimestral
    union all
    select * from mensual

)

select
    periodo_id,
    frecuencia,
    anio,
    trimestre,
    mes,
    fecha_inicio,
    fecha_fin,
    cast(anio as varchar) as periodo_anio_id
from unido
