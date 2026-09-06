-- B-031 / B-032: la fila de total departamental (renglon 999) debe ser la suma de las municipales por
-- (fuente, corte, departamento, bloque, columna), con la tolerancia relativa de cada fuente (vars).
with agg as (
    select fuente, fecha_corte, dpto_ccdgo, tipo_id, columna,
           sum(case when es_total_departamental then valor end)      as total_999,
           sum(case when not es_total_departamental then valor end)  as suma_municipal
    from {{ ref('int_sfc_geo_long') }}
    group by 1, 2, 3, 4, 5
)
select *,
       abs(total_999 - suma_municipal) / greatest(abs(suma_municipal), 1) as dif_relativa
from agg
where total_999 is not null and suma_municipal is not null
  and abs(total_999 - suma_municipal) > greatest(abs(suma_municipal), 1) * (
        case fuente
            when 'ptgf' then {{ var('sfc_total_tol_ptgf') }}
            else {{ var('sfc_total_tol_kx2f') }}
        end
      )
