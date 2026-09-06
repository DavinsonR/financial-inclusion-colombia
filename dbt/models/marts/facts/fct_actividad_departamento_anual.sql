-- Actividad económica departamental anual: PIB del DANE (corriente, constante 2015 y per cápita) más la
-- población por área. El agregado nacional (dpto_ccdgo = '00') se excluye: vive en su propia consulta.
-- `estado_dato` viaja con la fila porque el DANE revisa toda la serie cada julio (ADR-002).

with pib as (

    select * from {{ ref('stg_dane__pib_departamento_anual') }} where dpto_ccdgo <> '00'

),

poblacion as (

    select
        dpto_ccdgo,
        anio,
        max(case when area = 'total'    then poblacion end) as poblacion_total,
        max(case when area = 'cabecera' then poblacion end) as poblacion_cabecera,
        max(case when area = 'resto'    then poblacion end) as poblacion_resto
    from {{ ref('stg_dane__poblacion_departamento_anual') }}
    group by 1, 2

)

select
    p.dpto_ccdgo,
    p.anio,
    p.periodo_id,
    p.estado_dato,
    p.pib_corriente_mm,
    p.pib_constante_2015_mm,
    p.pib_per_capita_corriente,
    pob.poblacion_total,
    pob.poblacion_cabecera,
    pob.poblacion_resto,
    case when pob.poblacion_total > 0
         then p.pib_constante_2015_mm * 1e9 / pob.poblacion_total end   as pib_real_per_capita,
    case when pob.poblacion_total > 0
         then pob.poblacion_cabecera * 1.0 / pob.poblacion_total end     as tasa_urbanizacion
from pib as p
left join poblacion as pob on pob.dpto_ccdgo = p.dpto_ccdgo and pob.anio = p.anio
