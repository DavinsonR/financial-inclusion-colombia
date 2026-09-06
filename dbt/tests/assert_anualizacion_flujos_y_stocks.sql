-- La regla de anualización debe cumplirse fila a fila: un flujo con los cuatro trimestres vale su suma y
-- un stock vale su cuarto trimestre. Falla si algún valor anual se aparta de su definición.
select
    dpto_ccdgo,
    variable_id,
    anio,
    regla_anualizacion,
    trimestres_observados,
    valor_anual,
    suma_trimestres,
    valor_q4
from {{ ref('fct_inclusion_departamento_anual') }}
where (regla_anualizacion = 'sum'  and trimestres_observados = 4 and valor_anual is distinct from suma_trimestres)
   or (regla_anualizacion = 'sum'  and trimestres_observados < 4 and valor_anual is not null)
   or (regla_anualizacion = 'last' and valor_anual is distinct from valor_q4)
