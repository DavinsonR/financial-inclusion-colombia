-- Toda fila municipal de la SFC debe tener un mpio_ccdgo presente en dim_municipio (cobertura 100 %, S-009).
select l.fuente, l.fecha_corte, l.dpto_ccdgo, l.mpio_ccdgo, count(*) as filas
from {{ ref('int_sfc_geo_long') }} as l
left join {{ ref('dim_municipio') }} as d on d.mpio_ccdgo = l.mpio_ccdgo
where not l.es_total_departamental and d.mpio_ccdgo is null
group by 1, 2, 3, 4
