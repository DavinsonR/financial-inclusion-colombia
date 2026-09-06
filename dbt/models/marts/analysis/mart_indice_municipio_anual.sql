-- Índice de inclusión financiera por municipio y año, unido al panel municipal. Los pesos son los mismos
-- que en el departamental (calibrados allí), así que las dos escalas se pueden comparar.

select
    p.mpio_ccdgo,
    p.dpto_ccdgo,
    p.municipio,
    p.mpio_tipo,
    p.anio,
    p.periodo_id,
    i.iif_acceso,
    i.iif_uso,
    i.iif_profundidad,
    i.iif_compuesto,
    i.dimensiones_observadas,
    i.iif_pca                                as iif_sensibilidad_pca,
    i.iif_sarma                              as iif_sensibilidad_sarma,
    p.va_per_capita_corriente,
    p.crecimiento_va_pc_nominal,
    p.poblacion_total,
    p.tasa_urbanizacion
from {{ ref('mart_panel_municipio_anual') }} as p
left join {{ source('indice', 'indice_municipio_anual') }} as i
    on i.mpio_ccdgo = p.mpio_ccdgo and i.anio = p.anio
