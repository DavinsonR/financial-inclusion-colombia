# ADR-007 · Crosswalk nombre a DIVIPOLA por departamento, con overrides

- Fecha: 2026-09-06
- Estado: aceptada

## Contexto

La tabla vigente de la SFC (`kx2f-xjdq`) no trae códigos DIVIPOLA. Identifica el departamento con `unicap` (1 a 33 en numeración interna; 34 = total nacional; 35 a 42 = bloques de producto no geográficos) y el municipio por nombre en texto libre, con tres variantes mojibake en `tipo`, acentos inconsistentes y alias como `BOGOTA D C` o `CARTAGENA DE INDIAS`. En 2025Q4 hay 1.068 municipios reales frente a 1.121 del MGN; unos 36 municipios sin fila son no observados, no ceros. MinTIC y MEN sí traen DIVIPOLA.

## Decisión

1. Primero el departamento: semilla `xw_sfc_departamento.csv` de 33 filas (`unicap` a `dpto_ccdgo`). Es pequeña, se revisa a mano y no cambia.
2. Después el municipio, dentro de cada departamento: normalización de texto (reparar mojibake, quitar acentos, mayúsculas, colapsar espacios), tabla de alias versionada, y emparejamiento contra `dim_municipio` filtrada por `dpto_ccdgo`. Emparejar dentro del departamento elimina casi todos los homónimos.
3. `overrides.csv` versionado para los casos que la normalización no resuelve; cada override lleva motivo.
4. Salida: `xw_sfc_municipio.csv` con `(unicap, nombre_normalizado) → mpio_ccdgo` e informe de no mapeados con su monto.
5. Pruebas dbt: unicidad, `relationships` a `dim_municipio`, `left(mpio_ccdgo, 2) = dpto_ccdgo`, cobertura por monto ≥ 99,5 % por trimestre y fuente, estabilidad de `(unicap, renglon)` en el tiempo.
6. El total departamental nunca se pierde: `fct_inclusion_departamento_trimestre` suma mapeados y no mapeados por `unicap`.

## Alternativas consideradas

- Emparejamiento difuso global (sin departamento): más falsos positivos entre homónimos (hay varios "Sucre", "Bolívar", "Córdoba").
- Usar un crosswalk externo (TerriData): no accesible desde la sesión y sin API (B-023).
- Descartar la SFC vigente y quedarse con `ptgf`: pierde 2021 a 2025.

## Consecuencias

- El crosswalk es un artefacto de datos versionado y probado, no un paso oculto en un notebook.
- Los municipios no observados se distinguen de los ceros (R-13).
- Cada trimestre nuevo puede añadir nombres; la prueba de cobertura avisa.

## Cómo revertirla

Sustituir `xw_sfc_municipio.csv` por otra fuente de correspondencia con las mismas columnas. Las pruebas dbt se mantienen.
