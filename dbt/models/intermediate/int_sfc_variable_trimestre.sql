{{ config(materialized='table') }}
-- depends_on: {{ ref('dim_variable') }}

-- La SFC en formato canónico: una fila por (nivel, unidad geográfica, trimestre, variable), con las dos
-- tablas ya empalmadas. Traduce la columna de cada fuente a su `variable_id` (dim_variable) y suma las
-- entidades, que es el agregado correcto: cada entidad reporta su propia parte del municipio.
--
-- Dos niveles, nunca mezclados (B-031):
--   `municipio`: suma de las filas municipales (renglon <> 999).
--   `departamento`: la fila de total departamental (renglon = 999) que reporta la propia entidad.
-- En 2021Q1, que existe en las dos tablas, se conserva kx2f y se guarda ptgf como `valor_fuente_anterior`
-- para poder medir el salto (ADR-009).

with largo as (

    select
        l.fuente,
        l.periodo_id,
        l.fecha_corte,
        l.dpto_ccdgo,
        l.mpio_ccdgo,
        l.es_total_departamental,
        l.columna,
        l.valor
    from {{ ref('int_sfc_geo_long') }} as l

),

variables as (

    select variable_id, 'ptgf' as fuente, ptgf_column as columna from {{ ref('dim_variable') }} where ptgf_column <> ''
    union all
    select variable_id, 'kx2f' as fuente, kx2f_column as columna from {{ ref('dim_variable') }} where kx2f_column <> ''

),

etiquetado as (

    select
        v.variable_id,
        l.fuente,
        l.periodo_id,
        l.fecha_corte,
        l.dpto_ccdgo,
        l.mpio_ccdgo,
        l.es_total_departamental,
        l.valor
    from largo as l
    join variables as v on v.fuente = l.fuente and v.columna = l.columna

),

agregado as (

    select
        variable_id,
        fuente,
        periodo_id,
        fecha_corte,
        case when es_total_departamental then 'departamento' else 'municipio' end as nivel,
        dpto_ccdgo,
        case when es_total_departamental then null else mpio_ccdgo end            as mpio_ccdgo,
        sum(valor)                                                                as valor,
        count(*)                                                                  as n_filas_entidad
    from etiquetado
    group by 1, 2, 3, 4, 5, 6, 7

),

-- 2021Q1 está en ptgf y en kx2f: se prefiere kx2f y se guarda el valor anterior al lado.
preferencia as (

    select
        a.*,
        row_number() over (
            partition by a.variable_id, a.periodo_id, a.nivel, a.dpto_ccdgo, coalesce(a.mpio_ccdgo, '')
            order by case a.fuente when 'kx2f' then 0 else 1 end
        ) as prioridad
    from agregado as a

)

select
    p.variable_id,
    p.nivel,
    p.dpto_ccdgo,
    p.mpio_ccdgo,
    p.periodo_id,
    p.fecha_corte,
    cast(extract(year from p.fecha_corte) as integer)     as anio,
    cast(extract(quarter from p.fecha_corte) as integer)  as trimestre,
    p.fuente,
    p.valor,
    p.n_filas_entidad,
    anterior.valor                                        as valor_fuente_anterior
from preferencia as p
left join preferencia as anterior
    on  anterior.prioridad = 2
    and anterior.variable_id = p.variable_id
    and anterior.periodo_id  = p.periodo_id
    and anterior.nivel       = p.nivel
    and anterior.dpto_ccdgo  = p.dpto_ccdgo
    and coalesce(anterior.mpio_ccdgo, '') = coalesce(p.mpio_ccdgo, '')
where p.prioridad = 1
