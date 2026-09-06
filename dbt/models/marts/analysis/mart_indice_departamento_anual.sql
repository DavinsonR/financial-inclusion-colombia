-- Índice de inclusión financiera por departamento y año, unido al panel: es la tabla que consumen el atlas
-- y la econometría. El cálculo vive en `src/iif/index/` (ADR-015) y llega aquí como Parquet.

select
    p.dpto_ccdgo,
    p.departamento,
    p.region,
    p.anio,
    p.periodo_id,
    i.iif_acceso,
    i.iif_uso,
    i.iif_profundidad,
    i.iif_compuesto,
    i.dimensiones_observadas,
    i.iif_pca                                as iif_sensibilidad_pca,
    i.iif_sarma                              as iif_sensibilidad_sarma,
    p.pib_real_per_capita,
    p.crecimiento_pib_real_pc,
    p.poblacion_total,
    p.tasa_urbanizacion,
    p.itaed_promedio_anual
from {{ ref('mart_panel_departamento_anual') }} as p
left join {{ source('indice', 'indice_departamento_anual') }} as i
    on i.dpto_ccdgo = p.dpto_ccdgo and i.anio = p.anio
