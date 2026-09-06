# ADR-006 · Artefactos del trabajo de grado congelados como insumo, no como resultado

- Fecha: 2026-09-06
- Estado: aceptada, con adenda (2026-09-06)

## Contexto

La auditoría encontró que el documento de la tesis no reproduce desde el notebook consolidado: 25 discrepancias en 40 filas de libro, todas las N de la Tabla 6 desplazadas en 33, 6 de 8 β distintos, una errata de tabla, y 13 cifras guardadas que nunca se comparan (B-014). El código que produjo el documento no está en la subida. La tesis está calificada y aprobada.

## Decisión

1. `data/legacy/panel_fintech_colombia_trimestral.{xlsx,parquet}`, `notebooks/legacy/TESIS_CONSOLIDADO.ipynb` y `docs/legacy/RESULTADOS_CONSOLIDADO_2.md` quedan congelados: solo lectura, sha256 en `data/legacy/SHA256SUMS` (R-06). Solo se limpiaron metadatos y rutas (B-015); ningún valor de datos cambió.
2. `src/iif/legacy/` es un port del notebook con dos modos. `mode="notebook"` reproduce el notebook tal cual, con sus defectos, para que el libro de verificación sea auditable. `mode="corrected"` activa las correcciones documentadas en la bitácora sin tocar la reproducción.
3. Las cifras del documento viven una sola vez en `config/tesis_documento.yaml`. El libro de verificación (`ledger.py`) compara cada cifra obtenida con la del documento y publica OK, DISCREPA, SIN DATO EN DOC o DIAGNÓSTICO.
4. La tabla de discrepancias se publica en `docs/legacy/reproduccion.md` y en el sitio (`reproduccion-tesis.qmd`) con una columna de causa cuando se conozca.
5. Se dice en el README, sin rodeos, que documento y código divergen.

## Alternativas consideradas

- Corregir el notebook para que cuadre con el documento: sería inventar el código que no está.
- No publicar las discrepancias: contradice R-09 y el propósito del proyecto.
- Publicar solo la reproducción sin comparar con el documento: pierde la información más útil para un lector.

## Consecuencias

- Cualquiera puede correr `make reproduce` y obtener las mismas 40 filas.
- Las pruebas doradas de `tests/` fijan KMO 0,7189, Bartlett 2543,45, 84,42 % de varianza, la Tabla 6 A1 a B4 y el conteo de 25 discrepancias (pendientes de escribir).
- Extender el libro a las 13 cifras sin comparar es tarea abierta (B-014).

## Cómo revertirla

No se revierte: es un registro histórico. Si aparece el código original del documento, se añade como segundo artefacto congelado y el libro compara tres columnas.

## Adenda 2026-09-06: los resultados de la tesis no se publican

El autor decidió que el trabajo de grado es el borrador del proyecto y que ninguno de sus resultados debe aparecer como resultado del proyecto. En consecuencia:

1. Se retira la página `reproduccion-tesis.qmd` del sitio y toda cifra de la tesis del README (resultado, diagnósticos, tabla de discrepancias, N efectivo).
2. Los tres artefactos siguen congelados en `data/legacy/`, `notebooks/legacy/` y `docs/legacy/` como insumo histórico y como evidencia de la bitácora, con su sha256.
3. `src/iif/legacy/` y `make reproduce` se conservan como herramienta de auditoría interna: son lo que sostiene las entradas B-001 a B-015 y lo que permitió descubrir hechos sobre las fuentes que sí valen (B-031). Su salida vive en `docs/legacy/reproduccion.md`, fuera de la navegación del sitio.
4. Los puntos 4 y 5 de la decisión original quedan sin efecto.
