-- R-09: toda cifra publicada traza a una prueba. Cada fila es una cifra que aparece en la documentación, con
-- dónde se publica y sobre qué muestra se mide (B-049). Falla (devuelve la fila) si el warehouse deja de
-- producirla; entonces se corrige el documento o el modelo, nunca solo esta prueba.
--   docs/GUIA_DEL_PROYECTO.md: panel departamental 2018-2025 con 264 filas y 231 observaciones de
--     crecimiento; panel municipal 2018-2024 con 7.861 filas y 1.123 municipios.
--   README (tabla de fuentes) y dim_municipio: 1.121 municipios del MGN 2024.
--   fct_inclusion_departamento_trimestre: 96 de las 98 variables; dim_variable: 70 en ambas, 8 solo ptgf,
--     20 solo kx2f; dim_canal: 19 códigos, 17 en vkbt; stg_sfc__ptgf: 603.232 filas (tabla legada cerrada).
--   Bitácora S-012: mediana del crecimiento real per cápita de -9,3 % en 2020 y +8,4 % en 2021 (tolerancia
--     de media décima, que es el redondeo publicado; el DANE revisa el PIB cada julio y puede moverla).
with medidas as (

    select 'panel_departamento_filas' as cifra, cast(count(*) as {{ type_double() }}) as obtenido, 264.0 as esperado, 0.0 as tolerancia
    from {{ ref('mart_panel_departamento_anual') }}
    union all
    select 'panel_departamento_crecimientos', count(crecimiento_pib_real_pc), 231.0, 0.0
    from {{ ref('mart_panel_departamento_anual') }}
    union all
    select 'panel_municipio_filas', count(*), 7861.0, 0.0
    from {{ ref('mart_panel_municipio_anual') }}
    union all
    select 'panel_municipio_municipios', count(distinct mpio_ccdgo), 1123.0, 0.0
    from {{ ref('mart_panel_municipio_anual') }}
    union all
    select 'dim_municipio_en_mgn', sum(case when en_mgn then 1 else 0 end), 1121.0, 0.0
    from {{ ref('dim_municipio') }}
    union all
    select 'variables_departamentales', count(distinct variable_id), 96.0, 0.0
    from {{ ref('fct_inclusion_departamento_trimestre') }}
    union all
    select 'dim_variable_filas', count(*), 98.0, 0.0
    from {{ ref('dim_variable') }}
    union all
    select 'dim_variable_ambas', sum(case when disponible_en = 'ambas' then 1 else 0 end), 70.0, 0.0
    from {{ ref('dim_variable') }}
    union all
    select 'dim_variable_solo_ptgf', sum(case when disponible_en = 'ptgf' then 1 else 0 end), 8.0, 0.0
    from {{ ref('dim_variable') }}
    union all
    select 'dim_variable_solo_kx2f', sum(case when disponible_en = 'kx2f' then 1 else 0 end), 20.0, 0.0
    from {{ ref('dim_variable') }}
    union all
    select 'dim_canal_codigos', count(*), 19.0, 0.0
    from {{ ref('dim_canal') }}
    union all
    select 'dim_canal_en_vkbt', sum(case when en_vkbt then 1 else 0 end), 17.0, 0.0
    from {{ ref('dim_canal') }}
    union all
    select 'stg_sfc_ptgf_filas', count(*), 603232.0, 0.0
    from {{ ref('stg_sfc__ptgf') }}
    union all
    select 'mediana_crecimiento_2020_pct', 100 * {{ median_agg('crecimiento_pib_real_pc') }}, -9.3, 0.05
    from {{ ref('mart_panel_departamento_anual') }}
    where anio = 2020
    union all
    select 'mediana_crecimiento_2021_pct', 100 * {{ median_agg('crecimiento_pib_real_pc') }}, 8.4, 0.05
    from {{ ref('mart_panel_departamento_anual') }}
    where anio = 2021

)

select *
from medidas
where obtenido is null or abs(obtenido - esperado) > tolerancia
