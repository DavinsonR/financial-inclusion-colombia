-- En la tabla legada (ptgf) el total departamental es exactamente la suma de sus municipios. Esta prueba
-- vigila que los dos hechos, construidos por caminos distintos, sigan coincidiendo ahí.
-- En kx2f la propia fuente difiere hasta 2,2 % desde 2022Q3 (B-032), por eso solo se comprueba ptgf.
with mun as (
    select dpto_ccdgo, variable_id, periodo_id, sum(valor) as suma
    from {{ ref('fct_inclusion_municipio_trimestre') }}
    where fuente = 'ptgf'
    group by 1, 2, 3
),
dep as (
    select dpto_ccdgo, variable_id, periodo_id, valor
    from {{ ref('fct_inclusion_departamento_trimestre') }}
    where fuente = 'ptgf'
)
select dep.*, mun.suma, abs(dep.valor - mun.suma) as diferencia
from dep join mun using (dpto_ccdgo, variable_id, periodo_id)
where abs(dep.valor - mun.suma) > 1e-6 * greatest(abs(mun.suma), 1)
