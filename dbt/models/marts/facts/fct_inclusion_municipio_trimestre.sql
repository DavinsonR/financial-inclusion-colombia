-- Hecho trimestral por municipio y variable: suma de las entidades que reportan en ese municipio.
-- Un municipio sin fila en un trimestre es un no observado, no un cero (R-13): aquí simplemente no existe.

select
    m.mpio_ccdgo,
    m.dpto_ccdgo,
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
join {{ ref('dim_municipio') }} as m on m.mpio_ccdgo = s.mpio_ccdgo
join {{ ref('dim_variable') }}  as v on v.variable_id = s.variable_id
where s.nivel = 'municipio'
