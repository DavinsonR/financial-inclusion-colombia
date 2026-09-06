-- Colombia tiene 32 departamentos más Bogotá D.C.: dim_departamento debe tener 33 filas, ni una más.
select count(*) as n_filas
from {{ ref('dim_departamento') }}
having count(*) <> 33
