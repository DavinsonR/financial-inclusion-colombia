-- La numeración interna de departamentos (unicap 1-33) de ptgf-ywrb y kx2f-xjdq debe llevar al mismo
-- DIVIPOLA; si difieren, el empalme 2021Q1 mezclaría departamentos.
with k as (select unicap, dpto_ccdgo from {{ ref('xw_sfc_departamento') }} where fuente = 'kx2f'),
     p as (select unicap, dpto_ccdgo from {{ ref('xw_sfc_departamento') }} where fuente = 'ptgf')
select coalesce(k.unicap, p.unicap) as unicap, k.dpto_ccdgo as dpto_kx2f, p.dpto_ccdgo as dpto_ptgf
from k full outer join p on k.unicap = p.unicap
where k.dpto_ccdgo is null or p.dpto_ccdgo is null or k.dpto_ccdgo <> p.dpto_ccdgo
