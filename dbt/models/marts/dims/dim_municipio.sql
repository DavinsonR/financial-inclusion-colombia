-- Dimensión de municipios: unión del MGN 2024 (1.121: 1.102 municipios, 18 áreas no municipalizadas y 1 isla)
-- con los códigos que el DANE usa en valor agregado y población (1.123: añade 27493 Nuevo Belén de Bajirá y
-- 94663 Mapiripana, sin polígono en el MGN 2024) y con la semilla dim_municipio_extra (27086, el código
-- DIVIPOLA 2022 de Belén de Bajirá que usa la SFC). Clave natural DIVIPOLA `mpio_ccdgo`. ADR-013: las ANM se
-- conservan con su tipo; Bogotá (11001) es municipio y departamento a la vez.

with mgn as (

    select * from {{ ref('stg_mgn__municipios') }}

),

dane as (

    select mpio_ccdgo, dpto_ccdgo, max(municipio) as nombre_dane
    from {{ ref('stg_dane__poblacion_municipio_anual') }}
    group by 1, 2

),

extra as (

    select * from {{ ref('dim_municipio_extra') }}

),

codigos as (

    select mpio_ccdgo, dpto_ccdgo from mgn
    union
    select mpio_ccdgo, dpto_ccdgo from dane
    union
    select mpio_ccdgo, dpto_ccdgo from extra

)

select
    c.mpio_ccdgo,
    c.dpto_ccdgo,
    coalesce(mgn.nombre_mgn, dane.nombre_dane, extra.municipio)  as municipio,
    {{ normalize_geo_name('coalesce(mgn.nombre_mgn, dane.nombre_dane, extra.municipio)') }} as nombre_normalizado,
    coalesce(mgn.mpio_tipo, extra.mpio_tipo, 'M')       as mpio_tipo,
    mgn.area_km2,
    mgn.mpio_ccdgo is not null                          as en_mgn,
    dane.mpio_ccdgo is not null                         as en_dane,
    extra.motivo                                        as nota,
    c.mpio_ccdgo = c.dpto_ccdgo || '001'                as es_capital
from codigos as c
left join mgn on mgn.mpio_ccdgo = c.mpio_ccdgo
left join dane on dane.mpio_ccdgo = c.mpio_ccdgo
left join extra on extra.mpio_ccdgo = c.mpio_ccdgo
