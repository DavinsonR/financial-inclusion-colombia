# ADR-001 · Frecuencia anual y dos paneles

- Fecha: 2026-09-06
- Estado: aceptada

## Contexto

El panel de la tesis tenía 33 departamentos por 14 trimestres (2017Q4 a 2021Q1). Las series de la SFC son trimestrales, pero el PIB, la población, el internet, la educación, el IPC y el empleo son anuales y se copiaron en los cuatro trimestres (B-001). La dependiente tiene 5 valores por departamento; el 64,3 % de sus diferencias intra-anuales son cero. N efectivo = 165 departamento-años, no 462. El modelo dinámico regresaba la dependiente sobre una copia de sí misma.

No existe PIB trimestral subnacional en Colombia. El ITAED del DANE cubre 13 departamentos, Bogotá y un "resto" desde 2015Q1. El valor agregado municipal es anual (2011 a 2024p).

## Decisión

1. El grano de estimación es anual. Ninguna variable anual se repite en trimestres (R-05).
2. Dos paneles principales: departamental 2018 a 2025 (33 unidades, PIB del DANE, 2025 preliminar) y municipal 2018 a 2024 (valor agregado municipal, etiquetado como distribución).
3. Un tercer panel trimestral real, solo donde hay ITAED (13 departamentos más Bogotá), como complemento.
4. Las series trimestrales de la SFC se anualizan con una regla por variable: flujos, suma de los cuatro trimestres exigiendo los cuatro; stocks, valor del cuarto trimestre. La regla vive en `dbt/seeds/dim_variable.csv`.
5. La desagregación temporal (Chow-Lin, Denton) solo entra como anexo (ADR-010).

## Alternativas consideradas

- Mantener el panel trimestral con anuales repetidos: es el defecto que se corrige.
- Desagregar el PIB a trimestres con ITAED y estimar en trimestral: la variación intra-anual sería fabricada por el método y la inferencia lo ignoraría.
- Solo un panel departamental: pierde el nivel municipal que pidió el jurado y la variación transversal que da poder al panel corto.

## Consecuencias

- T = 8 en el departamental y 7 en el municipal. Poco T, mucho N en el municipal (más de 1.000 municipios).
- El sesgo de Nickell se evalúa con ese T efectivo, no con 14 (B-011).
- Las pruebas de raíz unitaria de panel y la dependencia transversal se tratan con métodos para T corto (CIPS, CCE).
- La reproducción de la tesis conserva el panel trimestral repetido a propósito (ADR-006).

## Cómo revertirla

Un ADR nuevo que declare el grano trimestral, con la regla `is_annual` de `dim_variable.csv` cambiada y la prueba de "sin valores anuales repetidos" desactivada de forma explícita. No hay atajo: los marts anuales dependen de la regla de anualización.
