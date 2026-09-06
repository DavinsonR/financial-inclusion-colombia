-- Hecho trimestral por departamento y variable. Usa la fila de total departamental que reporta la SFC
-- (renglon = 999), no la suma de municipios: las dos coinciden en ptgf y difieren hasta 2,2 % en kx2f
-- desde 2022Q3 (B-032), y el total de la fuente es el dato oficial.

select
    d.dpto_ccdgo,
    v.variable_id,
    s.periodo_id,
    s.anio,
    s.trimestre,
    s.fecha_corte,
    s.fuente,
    v.dimension_iif,
    v.bloque,
    v.unidad,
    v.naturaleza,
    s.valor,
    s.valor_fuente_anterior,
    s.n_filas_entidad
from {{ ref('int_sfc_variable_trimestre') }} as s
join {{ ref('dim_departamento') }} as d on d.dpto_ccdgo = s.dpto_ccdgo
join {{ ref('dim_variable') }}     as v on v.variable_id = s.variable_id
where s.nivel = 'departamento'
