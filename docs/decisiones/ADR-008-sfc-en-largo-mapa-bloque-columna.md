# ADR-008 · SFC en formato largo con mapa bloque a columna

- Fecha: 2026-09-06
- Estado: aceptada

## Contexto

Las tablas de la SFC son anchas (99 columnas en `kx2f-xjdq`) y cada fila pertenece a un bloque de producto (`unicap` o `renglon`) que solo usa un subconjunto de columnas. Fuera de ese subconjunto, Socrata rellena con cero, no con nulo. Los nombres de columna están truncados y son ambiguos; el esquema cambió en 2021Q1. El panel de la tesis heredó esos ceros como valores y dejó 81 de 102 columnas sin usar (B-013).

## Decisión

1. Staging en formato largo: `(fuente, periodo, entidad, unicap, renglon, municipio_texto, variable, valor)`.
2. Un mapa bloque a columna en `dbt/seeds/map_sfc_columns.csv`, derivado de los datos con `iif crosswalk derive-blocks` y revisado a mano, dice qué columnas pertenecen a cada bloque.
3. El unpivot emite un valor solo si la columna pertenece al bloque de la fila. Los ceros fuera de bloque desaparecen estructuralmente, no por una regla `nullif`.
4. Dentro del bloque, un cero es un cero. La ausencia de fila es no observado (NULL). `n_entidades` acompaña cada agregado para distinguir "cero reportado" de "nadie reportó".
5. `dim_variable.csv` guarda, por variable, la columna en `ptgf` y la columna en `kx2f`; ese es el mapa del empalme (ADR-009).
6. Los bloques 34 a 42 (total nacional y productos no geográficos) van a `fct_sfc_nacional_trimestre`, no al panel geográfico.

## Alternativas consideradas

- Mantener el formato ancho y limpiar ceros por regla: frágil, cada columna nueva exige una regla nueva.
- `nullif(valor, 0)` en todo: borra ceros reales (un municipio sin microcrédito en un trimestre es un cero).
- Un modelo por bloque: multiplica modelos y pruebas sin ganar claridad.

## Consecuencias

- Las tablas largas son grandes (decenas de millones de filas en kx2f); DuckDB las maneja en local y Snowflake en producción.
- Añadir una variable es una fila en dos semillas, no código nuevo (R-15).
- La regla R-13 tiene una implementación concreta y probada.

## Cómo revertirla

Los marts anchos se derivan de la tabla larga con un pivot; nada del análisis lee el staging directamente. Cambiar la representación interna no toca los marts.
