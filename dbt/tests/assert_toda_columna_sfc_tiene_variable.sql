-- Toda columna numérica registrada en map_sfc_columns debe tener su variable en dim_variable, en la fuente
-- correspondiente. Si la SFC añade columnas, esta prueba falla hasta que se regenere el diccionario.
with columnas as (
    select fuente, columna from {{ ref('map_sfc_columns') }}
),
variables as (
    select 'ptgf' as fuente, ptgf_column as columna from {{ ref('dim_variable') }} where ptgf_column is not null and ptgf_column <> ''
    union all
    select 'kx2f' as fuente, kx2f_column as columna from {{ ref('dim_variable') }} where kx2f_column is not null and kx2f_column <> ''
)
select c.*
from columnas as c
left join variables as v on v.fuente = c.fuente and v.columna = c.columna
where v.columna is null
