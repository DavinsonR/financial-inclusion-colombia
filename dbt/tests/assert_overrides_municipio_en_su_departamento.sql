-- Una corrección manual del crosswalk municipal debe apuntar a un municipio del mismo departamento que su
-- unidad de captura. `unicap` es la numeración interna de la SFC (1 = Antioquia = '05'), así que el prefijo
-- se compara con el DIVIPOLA que da xw_sfc_departamento, nunca con lpad(unicap).
select o.fuente, o.unicap, o.renglon, o.mpio_ccdgo, x.dpto_ccdgo
from {{ ref('xw_sfc_municipio_overrides') }} as o
left join {{ ref('xw_sfc_departamento') }} as x
    on x.fuente = o.fuente and x.unicap = o.unicap
where o.mpio_ccdgo is not null
  and (x.dpto_ccdgo is null or left(o.mpio_ccdgo, 2) <> x.dpto_ccdgo)
