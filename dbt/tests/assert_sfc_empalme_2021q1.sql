-- ADR-009: 2021Q1 existe en ptgf y en kx2f. Por departamento, la mediana de la diferencia relativa entre
-- los totales departamentales (renglon 999) de las columnas emparejadas (xw_sfc_columns_empalme) no debe
-- superar overlap_median_pct. Primeros valores (2026-09-06): mediana global 0,02 %; peor departamento
-- Antioquia 1,8 %; por bloque, corresponsales físicos 3,4 % y microcrédito con p90 de 12 % (B-033).
with totales as (
    select fuente, dpto_ccdgo, columna, sum(valor) as valor
    from {{ ref('int_sfc_geo_long') }}
    where periodo_id = '2021Q1' and es_total_departamental
    group by 1, 2, 3
),
pares as (
    select p.dpto_ccdgo,
           e.ptgf_column,
           e.kx2f_column,
           p.valor as v_ptgf,
           k.valor as v_kx2f
    from totales as p
    join {{ ref('xw_sfc_columns_empalme') }} as e on e.ptgf_column = p.columna and p.fuente = 'ptgf'
    join totales as k on k.fuente = 'kx2f' and k.dpto_ccdgo = p.dpto_ccdgo and k.columna = e.kx2f_column
    where p.valor <> 0
),
por_dpto as (
    select dpto_ccdgo,
           count(*)                                                as pares,
           median(abs(v_kx2f - v_ptgf) / abs(v_ptgf))              as mediana_rel
    from pares
    group by 1
)
select * from por_dpto
where mediana_rel > {{ var('overlap_median_pct') }} / 100.0
