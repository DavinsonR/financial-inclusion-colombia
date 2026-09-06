# ADR-009 · Empalme ptgf/kx2f validado en 2021Q1, con preferencia por kx2f

- Fecha: 2026-09-06
- Estado: aceptada

## Contexto

La SFC publica dos tablas: `ptgf-ywrb` (2017Q4 a 2021Q1, congelada, con cuentas de ahorro electrónicas y `unicap` 37 como bloque no geográfico) y `kx2f-xjdq` (2021Q1 a 2025Q4, vigente, sin DIVIPOLA). El trimestre 2021Q1 aparece en ambas con esquemas distintos. Es la única superposición y sirve como prueba natural del empalme (S-002).

## Decisión

1. Ambas tablas se cargan en largo (ADR-008) y se unen con `UNION ALL` y una columna `fuente`.
2. En 2021Q1 se conserva la fila de `kx2f` y se guarda la diferencia frente a `ptgf` por departamento y variable en una tabla auxiliar.
3. Prueba singular de dbt: falla si la mediana de diferencias relativas por departamento supera 2 % o si algún departamento supera 10 %. Los primeros números se anotan en la bitácora antes de fijar los umbrales definitivos.
4. `dim_variable.csv` es el mapa del empalme: una fila por variable con su columna en cada esquema. Una variable sin columna en uno de los dos esquemas se marca y no entra al panel largo (por ejemplo las CAE, ADR-004).
5. `test_legacy_vs_ptgf` reconstruye las columnas 8 a 85 del xlsx de la tesis desde `ptgf` y exige que al menos el 90 % de las columnas coincidan dentro de 0,5 %. Eso valida a la vez el panel legado y el staging.

## Alternativas consideradas

- Preferir `ptgf` en 2021Q1: es la tabla congelada; `kx2f` es la que la SFC mantiene y corrige.
- Promediar: mezcla dos definiciones y oculta la ruptura.
- Usar solo `kx2f`: pierde 2017Q4 a 2020Q4 y la comparación con la tesis.

## Consecuencias

- La serie larga tiene una ruptura documentada en 2021Q1 con su magnitud medida por variable.
- Los modelos de fase 3 pueden incluir un indicador de esquema o probar la sensibilidad al empalme.
- Si la diferencia en alguna variable es grande, esa variable se excluye del panel largo con nota, no se ajusta a mano.

## Cómo revertirla

La preferencia en 2021Q1 es un `CASE` en `int_sfc_geo_long`. Los umbrales de la prueba están en la prueba singular. Cambiar cualquiera exige actualizar este ADR.
