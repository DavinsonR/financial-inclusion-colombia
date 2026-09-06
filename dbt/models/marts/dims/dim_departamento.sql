-- Dimensión de departamentos (33 = 32 departamentos + Bogotá D.C.), clave natural DIVIPOLA `dpto_ccdgo`.
-- Une la región del notebook legado con la numeración interna de la SFC (`unicap`, idéntica en ptgf y kx2f;
-- lo garantiza tests/assert_sfc_unicap_consistente_entre_fuentes.sql) y guarda el nombre legado y una
-- clave normalizada para cruces por nombre.

with region as (

    select * from {{ ref('xw_departamento_region') }}

),

sfc as (

    select
        unicap      as sfc_unicap,
        descrip_uc  as sfc_descrip_uc,
        dpto_ccdgo
    from {{ ref('xw_sfc_departamento') }}
    where fuente = 'kx2f'

)

select
    region.dpto_ccdgo,
    region.departamento,
    region.nombre_corto,
    region.nombre_legacy,
    {{ normalize_geo_name('region.departamento') }}    as nombre_normalizado,
    region.region_id,
    region.region,
    sfc.sfc_unicap,
    sfc.sfc_descrip_uc
from region
left join sfc
    on sfc.dpto_ccdgo = region.dpto_ccdgo
