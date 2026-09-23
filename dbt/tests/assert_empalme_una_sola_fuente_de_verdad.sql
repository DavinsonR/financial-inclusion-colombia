-- R-15: la correspondencia ptgf -> kx2f vive en dos semillas, dim_variable (ptgf_column, kx2f_column), que es
-- la que usan los modelos (ADR-008, punto 5), y xw_sfc_columns_empalme, de la que se derivó y que usa la
-- prueba del empalme 2021Q1. Mientras existan las dos, deben decir exactamente lo mismo en ambos sentidos.
with dv as (
    select ptgf_column, kx2f_column from {{ ref('dim_variable') }} where ptgf_column is not null
),
xw as (
    select ptgf_column, kx2f_column from {{ ref('xw_sfc_columns_empalme') }}
)
select 'solo en dim_variable' as donde, dv.ptgf_column, dv.kx2f_column
from dv
left join xw on xw.ptgf_column = dv.ptgf_column
where xw.ptgf_column is null or xw.kx2f_column is distinct from dv.kx2f_column
union all
select 'solo en xw_sfc_columns_empalme', xw.ptgf_column, xw.kx2f_column
from xw
left join dv on dv.ptgf_column = xw.ptgf_column
where dv.ptgf_column is null
