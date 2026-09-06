-- Actividad económica municipal anual: valor agregado del DANE (2011 a 2024p) más población.
-- Advertencia que viaja con el dato (ADR-001): el valor agregado municipal es una DISTRIBUCIÓN del PIB
-- departamental con indicadores, no una medición municipal independiente. `peso_relativo_pct` es
-- exactamente ese reparto, y por eso se conserva a la vista.

with va as (

    select * from {{ ref('stg_dane__va_municipio_anual') }}

),

poblacion as (

    select
        mpio_ccdgo,
        anio,
        max(case when area = 'total'    then poblacion end) as poblacion_total,
        max(case when area = 'cabecera' then poblacion end) as poblacion_cabecera,
        max(case when area = 'resto'    then poblacion end) as poblacion_resto
    from {{ ref('stg_dane__poblacion_municipio_anual') }}
    group by 1, 2

)

select
    v.mpio_ccdgo,
    v.dpto_ccdgo,
    v.anio,
    v.periodo_id,
    v.estado_dato,
    v.va_corriente_mm,
    v.va_primarias_mm,
    v.va_secundarias_mm,
    v.va_terciarias_mm,
    v.peso_relativo_pct,
    p.poblacion_total,
    p.poblacion_cabecera,
    p.poblacion_resto,
    case when p.poblacion_total > 0
         then v.va_corriente_mm * 1e9 / p.poblacion_total end        as va_per_capita_corriente,
    case when p.poblacion_total > 0
         then p.poblacion_cabecera * 1.0 / p.poblacion_total end      as tasa_urbanizacion
from va as v
left join poblacion as p on p.mpio_ccdgo = v.mpio_ccdgo and p.anio = v.anio
