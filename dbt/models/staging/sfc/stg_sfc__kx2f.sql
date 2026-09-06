{{ config(materialized='view') }}
-- depends_on: {{ ref('map_sfc_columns') }}

-- Tabla vigente de inclusión financiera de la SFC (2021Q1 a 2025Q4, 99 columnas), con claves resueltas:
--   * dpto_ccdgo por `unicap` (semilla xw_sfc_departamento);
--   * mpio_ccdgo = dpto_ccdgo || lpad(renglon, 3) para las filas municipales (S-009, ADR-007);
--   * es_total_departamental cuando renglon = 999: esa fila YA es la suma de las municipales (B-031);
--   * tipo_id por la semilla map_sfc_tipo (tres grafías de 'Corresponsales físicos'); las columnas numéricas
--     son las 90 que registra map_sfc_columns
--     (una por bloque): fuera de su bloque solo traen ceros estructurales (ADR-008).
-- No agrega ni corrige valores: es la fuente tal cual, tipada.

{% set cols = [] %}
{% if execute %}
    {% set cols = run_query(
        "select distinct columna from " ~ ref('map_sfc_columns') ~ " where fuente = 'kx2f' order by 1"
    ).columns[0].values() %}
{% endif %}

with fuente as (

    select * from {{ source('sfc', 'sfc_kx2f_xjdq') }}

),

xw as (

    select unicap, dpto_ccdgo from {{ ref('xw_sfc_departamento') }} where fuente = 'kx2f'

),

tipos as (

    select tipo_raw, tipo_id from {{ ref('map_sfc_tipo') }} where fuente = 'kx2f'

),

base as (

    select
        cast(f.fecha_corte as date)                  as fecha_corte,
        cast(f.unicap as integer)                   as unicap,
        cast(f.renglon as integer)                  as renglon,
        f.descrip_uc                                as nombre_unidad_raw,
        f.desc_renglon                              as nombre_renglon_raw,
        f.tipo                     as tipo_raw,
        cast(f.tipo_entidad as integer)              as tipo_entidad,
        cast(f.codigo_entidad as integer)            as codigo_entidad,
        f.nombre_entidad                            as nombre_entidad,
        f.pull_id,
        {% for c in cols %}
        cast(f.{{ c }} as double)                   as {{ c }}{{ "," if not loop.last }}
        {% endfor %}
    from fuente as f

)

select
    'kx2f'                                                              as fuente,
    b.fecha_corte,
    {{ periodo_id('b.fecha_corte', 'Q') }}                              as periodo_id,
    b.unicap,
    b.renglon,
    b.unicap <= 33                                                      as es_geografico,
    b.unicap <= 33 and b.renglon = 999                                  as es_total_departamental,
    xw.dpto_ccdgo,
    case
        when b.unicap <= 33 and b.renglon <> 999
        then xw.dpto_ccdgo || lpad(cast(b.renglon as varchar), 3, '0')
    end                                                                 as mpio_ccdgo,
    b.nombre_unidad_raw,
    b.nombre_renglon_raw,
    b.tipo_raw,
    t.tipo_id,
    b.tipo_entidad,
    b.codigo_entidad,
    b.nombre_entidad,
    b.pull_id,
    {% for c in cols %}
    b.{{ c }}{{ "," if not loop.last }}
    {% endfor %}
from base as b
left join xw on xw.unicap = b.unicap
left join tipos as t on t.tipo_raw = b.tipo_raw
