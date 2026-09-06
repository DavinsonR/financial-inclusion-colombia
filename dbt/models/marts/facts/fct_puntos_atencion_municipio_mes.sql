-- Puntos de atención por municipio, canal y mes (SFC vkbt, desde 2023-01). La fuente repite la clave
-- (corte, entidad, municipio, canal) en 1.199 casos con valores distintos y sin columna que los separe,
-- así que se suman: es el total del municipio, que es lo que se usa.

select
    p.mpio_ccdgo,
    p.dpto_ccdgo,
    p.codigo_canal,
    c.nombre_canal,
    c.grupo_canal,
    c.tipo_canal,
    p.periodo_id,
    p.fecha_corte,
    cast(extract(year from p.fecha_corte) as integer)  as anio,
    cast(extract(month from p.fecha_corte) as integer) as mes,
    sum(p.puntos_atencion)                             as puntos_atencion,
    sum(p.puntos_atencion_activos)                     as puntos_atencion_activos,
    count(distinct p.codigo_entidad)                   as n_entidades
from {{ ref('stg_sfc__vkbt') }} as p
left join {{ ref('dim_canal') }} as c on c.codigo_canal = p.codigo_canal
group by all
