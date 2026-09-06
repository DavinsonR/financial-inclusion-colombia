{{ config(materialized='table') }}
-- depends_on: {{ ref('map_sfc_columns') }}
-- depends_on: {{ ref('stg_sfc__ptgf') }}
-- depends_on: {{ ref('stg_sfc__kx2f') }}

-- Filas geográficas de la SFC (unicap 1-33) en formato largo: una fila por (fuente, corte, entidad, unidad,
-- bloque, columna). Solo se emite una columna cuando pertenece al bloque `tipo_id` de la fila
-- (semilla map_sfc_columns): así los ceros fuera de bloque desaparecen estructuralmente (ADR-008).
-- Las filas con es_total_departamental = true son el total del departamento (renglon 999) y NO deben
-- sumarse con las municipales (B-031). Fuentes: ptgf y kx2f (2021Q1 está en las dos; el empalme se decide en los marts, ADR-009).

{% set pares = [] %}
{% if execute %}
    {% set pares = run_query(
        "select fuente, tipo_id, columna from " ~ ref('map_sfc_columns') ~ " order by 1, 2, 3"
    ).rows %}
{% endif %}

{% for p in pares %}
select
    fuente,
    fecha_corte,
    periodo_id,
    dpto_ccdgo,
    mpio_ccdgo,
    es_total_departamental,
    tipo_id,
    tipo_entidad,
    codigo_entidad,
    pull_id,
    '{{ p[2] }}'    as columna,
    {{ p[2] }}      as valor
from {{ ref('stg_sfc__' ~ p[0]) }}
where es_geografico and tipo_id = '{{ p[1] }}'
{% if not loop.last %}
union all
{% endif %}
{% endfor %}
