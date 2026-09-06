{{ config(materialized='view') }}

-- Estadísticas de educación preescolar, básica y media por municipio y año (2011 a 2024).
-- Las tasas y coberturas en cero son faltantes (R-13, ADR-008): nullif(x, 0). La población 5-16 se deja tal cual.

{% set tasas = [
    'tasa_matriculaci_n_5_16', 'cobertura_neta', 'cobertura_neta_transici_n', 'cobertura_neta_primaria',
    'cobertura_neta_secundaria', 'cobertura_neta_media', 'cobertura_bruta', 'cobertura_bruta_transici_n',
    'cobertura_bruta_primaria', 'cobertura_bruta_secundaria', 'cobertura_bruta_media',
    'tama_o_promedio_de_grupo', 'deserci_n', 'deserci_n_transici_n', 'deserci_n_primaria',
    'deserci_n_secundaria', 'deserci_n_media', 'aprobaci_n', 'aprobaci_n_transici_n', 'aprobaci_n_primaria',
    'aprobaci_n_secundaria', 'aprobaci_n_media', 'reprobaci_n', 'reprobaci_n_transici_n',
    'reprobaci_n_primaria', 'reprobaci_n_secundaria', 'reprobaci_n_media', 'repitencia',
    'repitencia_transici_n', 'repitencia_primaria', 'repitencia_secundaria', 'repitencia_media'
] %}
{% set nombres = {
    'tasa_matriculaci_n_5_16': 'tasa_matriculacion_5_16', 'cobertura_neta_transici_n': 'cobertura_neta_transicion',
    'cobertura_bruta_transici_n': 'cobertura_bruta_transicion', 'tama_o_promedio_de_grupo': 'tamano_promedio_grupo',
    'deserci_n': 'desercion', 'deserci_n_transici_n': 'desercion_transicion', 'deserci_n_primaria': 'desercion_primaria',
    'deserci_n_secundaria': 'desercion_secundaria', 'deserci_n_media': 'desercion_media',
    'aprobaci_n': 'aprobacion', 'aprobaci_n_transici_n': 'aprobacion_transicion', 'aprobaci_n_primaria': 'aprobacion_primaria',
    'aprobaci_n_secundaria': 'aprobacion_secundaria', 'aprobaci_n_media': 'aprobacion_media',
    'reprobaci_n': 'reprobacion', 'reprobaci_n_transici_n': 'reprobacion_transicion', 'reprobaci_n_primaria': 'reprobacion_primaria',
    'reprobaci_n_secundaria': 'reprobacion_secundaria', 'reprobaci_n_media': 'reprobacion_media',
    'repitencia_transici_n': 'repitencia_transicion'
} %}

select
    cast(a_o as integer)                                    as anio,
    cast(a_o as varchar)                                    as periodo_id,
    lpad(cast(c_digo_departamento as varchar), 2, '0')      as dpto_ccdgo,
    lpad(cast(c_digo_municipio as varchar), 5, '0')         as mpio_ccdgo,
    municipio                                               as nombre_municipio_raw,
    c_digo_etc                                              as codigo_etc,
    etc,
    cast(poblaci_n_5_16 as double)                          as poblacion_5_16,
    cast(sedes_conectadas_a_internet as double)             as sedes_conectadas_internet,
    {% for c in tasas %}
    nullif(cast({{ c }} as double), 0)                      as {{ nombres.get(c, c) }}{{ "," if not loop.last }}
    {% endfor %},
    pull_id
from {{ source('men', 'men_nudc_7mev') }}
where lpad(cast(c_digo_municipio as varchar), 5, '0') <> '00000'  -- fila 'NACIONAL' (3 en 2011-2024): no es un municipio
