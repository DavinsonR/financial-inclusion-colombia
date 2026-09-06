-- Educación por municipio y año (MEN, 2011 a 2024). Los ceros de tasas ya son nulos en staging (R-13).
-- Quiebre metodológico en 2018: las series antes y después no son estrictamente comparables (ADR-008).

select
    mpio_ccdgo,
    dpto_ccdgo,
    anio,
    periodo_id,
    poblacion_5_16,
    tasa_matriculacion_5_16,
    cobertura_neta,
    cobertura_bruta,
    cobertura_neta_media,
    cobertura_bruta_media,
    desercion,
    aprobacion,
    reprobacion,
    repitencia,
    tamano_promedio_grupo,
    sedes_conectadas_internet,
    anio >= 2018 as despues_del_quiebre_2018
from {{ ref('stg_men__educacion') }}
