# ADR-002 · Estrella dimensional con vintages y claves naturales

- Fecha: 2026-09-06
- Estado: aceptada

## Contexto

El autor pidió una arquitectura distinta a medallion. Las fuentes tienen granos distintos (entidad por municipio por trimestre en la SFC; municipio por mes en puntos de atención; departamento por año en el DANE) y algunas se revisan enteras cada año (el DANE republica toda la serie del PIB en julio). Los nombres de columna de la SFC cambiaron de esquema en 2021Q1.

## Decisión

Un esquema estrella de Kimball en dbt, con capas staging, intermediate y marts:

- Dimensiones: `dim_departamento` (33; `dpto_ccdgo`, `sfc_unicap`, región), `dim_municipio` (1.121; `mpio_ccdgo`, tipo M, D o ANM), `dim_periodo` (anual, trimestral, mensual), `dim_entidad`, `dim_canal` (17), `dim_variable` (bloque, dimensión del IIF, unidad, stock o flujo, regla de anualización, columna en ptgf y en kx2f), `dim_vintage` (una fila por descarga: `pull_id`, `source_updated_at`, sha256, licencia, `is_current`).
- Hechos: uno por fuente y grano, todos con `pull_id`, `source_updated_at` e `is_current`. Los del DANE llevan `estado_dato` (definitivo, provisional, preliminar).
- Claves naturales (DIVIPOLA, código de entidad, periodo ISO), no sustitutas.
- Los hechos son bitemporales: fecha de referencia del dato y fecha de publicación de la fuente. Una revisión del DANE crea un vintage nuevo; el anterior no se borra.

## Alternativas consideradas

- Medallion (bronze, silver, gold): es lo que el autor ya hizo en otro proyecto y quería algo distinto; además no dice nada del modelo de datos.
- Data Vault: buen soporte de vintages, pero demasiada ceremonia (hubs, links, satellites) para seis fuentes y una persona.
- Una tabla ancha por panel: es el xlsx de la tesis; no escala a municipios ni a revisiones.

## Consecuencias

- Cada consulta de análisis filtra `is_current = true` o fija un `pull_id`. Las tablas de la tesis se reproducen con el vintage que corresponde.
- dbt prueba unicidad de claves, relaciones entre hechos y dimensiones, y aceptación de códigos.
- En Snowflake, `dim_vintage` se complementa con clonación de esquemas por vintage (ADR-014).

## Cómo revertirla

Los marts de análisis (`mart_panel_*`) son el contrato con la econometría y el atlas. Cambiar el modelo por debajo exige mantener esos marts con las mismas columnas o un ADR que los reemplace.
