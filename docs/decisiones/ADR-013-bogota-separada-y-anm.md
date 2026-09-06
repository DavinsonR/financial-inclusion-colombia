# ADR-013 · Bogotá separada en el panel departamental y áreas no municipalizadas conservadas

- Fecha: 2026-09-06
- Estado: aceptada

## Contexto

El DANE publica PIB departamental para 33 unidades: 32 departamentos y Bogotá D.C. La SFC usa `unicap` 1 a 33 con la misma lógica. La tesis estimó con 33 unidades. El MGN 2024 trae 1.121 municipios con tipo municipio (M), distrito (D) y área no municipalizada (ANM), estas últimas en Amazonas, Guainía y Vaupés. Con 33 unidades, el clúster de Bogotá tiene una sola observación por periodo y la ratio Bogotá/Cundinamarca queda separada en dos.

## Decisión

1. Bogotá es una unidad del panel departamental, separada de Cundinamarca. 33 unidades, como el DANE y la SFC. `dim_departamento` tiene 33 filas con `dpto_ccdgo = 11` para Bogotá.
2. En el panel municipal, Bogotá es un municipio (`mpio_ccdgo = 11001`) y Cundinamarca tiene sus 116.
3. Las áreas no municipalizadas se conservan en `dim_municipio` con `mpio_tipo = ANM`, con su código MGN, población `_VP` y geometría. Entran en los agregados departamentales. Los modelos de fase 3 pueden excluirlas con un filtro explícito y declarado, nunca por omisión.
4. Los municipios sin fila en la SFC son no observados (NULL), no ceros (R-13).

## Alternativas consideradas

- Fusionar Bogotá con Cundinamarca: pierde comparabilidad con el DANE y con la tesis; Bogotá es un tercio del PIB nacional y dominaría la unidad fusionada.
- Descartar las ANM: sesga los agregados de tres departamentos amazónicos hacia sus capitales.
- Agregar las ANM a la capital: inventa una unidad que no existe en el MGN.

## Consecuencias

- Los mapas del atlas muestran las ANM con su geometría real.
- Las pruebas de dbt exigen 33 departamentos y 1.121 municipios en las dimensiones.
- La heterogeneidad por región sigue usando 33 unidades; nunca submuestras de 4 clústeres (B-009).

## Cómo revertirla

Cambiar `dbt/seeds/xw_sfc_departamento.csv` y `dim_municipio` con un ADR nuevo. Las pruebas de conteo se ajustan en el mismo cambio.

## Adenda 2026-09-06: Belén de Bajirá

El municipio creado en 2022 tiene tres identidades: DIVIPOLA 27086 (la usa la SFC en `vkbt`), 27493 "Nuevo Belén de Bajirá" en las cuentas y proyecciones del DANE, y ningún polígono en el MGN 2024 (sigue dentro de Riosucio 27615 y Mutatá 05480). `dim_municipio` conserva los tres códigos con `en_mgn`, `en_dane` y una nota (semilla `dim_municipio_extra.csv`); el atlas los mostrará dentro de sus municipios de origen hasta que el MGN publique el límite.
