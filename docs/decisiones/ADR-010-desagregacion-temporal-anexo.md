# ADR-010 · Desagregación temporal solo como anexo

- Fecha: 2026-09-06
- Estado: aceptada

## Contexto

El autor quería más periodos. La SFC tiene trimestres, pero el PIB subnacional es anual (ADR-001). Existen métodos para repartir un total anual en trimestres: Chow-Lin (regresión sobre un indicador trimestral), Denton (suavizado que respeta el total) y Fernández. El ITAED del DANE es el único indicador trimestral oficial y cubre 13 departamentos más Bogotá. Una serie desagregada tiene variación intra-anual creada por el método; estimar sobre ella sin decirlo repite, con otra cara, el defecto B-001.

## Decisión

1. La desagregación temporal no entra en la estimación principal ni en el atlas.
2. Se produce un anexo (`anexos/desagregacion-temporal.qmd`) con Chow-Lin y Denton usando ITAED donde existe, con advertencias explícitas: la variación intra-anual es del método, la inferencia debe tratar la serie como generada, y los resultados se comparan con el panel anual.
3. MIDAS (inclusión trimestral, PIB anual) se ofrece como sensibilidad porque respeta las frecuencias reales; tampoco es la especificación de referencia.
4. Las series desagregadas se guardan en un mart aparte con `metodo` y `indicador` como columnas, nunca mezcladas con los hechos observados.

## Alternativas consideradas

- Estimar en trimestral sobre series desagregadas: rechazado por el motivo de arriba.
- Omitir la desagregación: pierde una pregunta legítima del autor y del jurado ("más periodos").
- Usar el ITAED como dependiente principal: cubre menos de la mitad de los departamentos.

## Consecuencias

- El anexo es una página `draft: true` hasta la fase 4.
- El lector ve qué cambia y qué no al desagregar; ninguna cifra del anexo se cita como resultado principal.

## Cómo revertirla

Un ADR nuevo que promueva un método a estimación principal, con la prueba de "sin valores anuales repetidos" adaptada para distinguir observado de generado.
