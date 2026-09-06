-- Casos de referencia de las macros repair_mojibake, normalize_geo_name y periodo_id, tomados de los
-- valores reales de la SFC (NARIﾑO en ptgf-ywrb; 'Corresponsales f' + U+00AD + 'sicos' en kx2f-xjdq).
-- Falla (devuelve filas) si alguna macro deja de producir el resultado esperado.
with casos as (

    select 1 as id, {{ repair_mojibake("'NARI' || chr(65425) || 'O'") }} as obtenido, 'NARIÑO' as esperado
    union all
    select 2, {{ repair_mojibake("'Corresponsales f' || chr(195) || chr(173) || 'sicos'") }}, 'Corresponsales físicos'
    union all
    select 3, {{ repair_mojibake("'Bogot' || chr(195) || chr(161) || ', D.C.'") }}, 'Bogotá, D.C.'
    union all
    select 4, {{ repair_mojibake("'NARI' || chr(195) || chr(8216) || 'O'") }}, 'NARIÑO'
    union all
    select 5, {{ repair_mojibake("'sin cambios'") }}, 'sin cambios'
    union all
    select 6, {{ normalize_geo_name("'San Andres,Prov Y Santa Catalina'") }}, 'SAN ANDRES PROV Y SANTA CATALINA'
    union all
    select 7, {{ normalize_geo_name("'Bogotá, D.C.'") }}, 'BOGOTA D C'
    union all
    select 8, {{ normalize_geo_name(repair_mojibake("'  NARI' || chr(65425) || 'O '")) }}, 'NARINO'
    union all
    select 9, {{ periodo_id("cast('2021-03-01' as date)", 'Q') }}, '2021Q1'
    union all
    select 10, {{ periodo_id("cast('2021-03-01' as date)", 'M') }}, '2021-03'
    union all
    select 11, {{ periodo_id("cast('2021-03-01' as date)", 'A') }}, '2021'

)

select id, obtenido, esperado
from casos
where obtenido is distinct from esperado
