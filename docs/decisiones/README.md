# Registros de decisiones (ADR)

Cada decisión de valor del proyecto se escribe aquí antes del código (R-11). Formato: título, fecha, estado, contexto, decisión, alternativas consideradas, consecuencias, cómo revertirla. Estados: propuesta, aceptada, reemplazada.

| ADR | Título | Estado |
|---|---|---|
| [001](ADR-001-frecuencia-anual.md) | Frecuencia anual y dos paneles | aceptada |
| [002](ADR-002-estrella-con-vintages.md) | Estrella dimensional con vintages y claves naturales | aceptada |
| [003](ADR-003-parquet-en-repo-releases-dvc.md) | Parquet en el repo por debajo de 45 MB, Releases como desborde, DVC diferido | aceptada |
| [004](ADR-004-indice-en-dos-etapas.md) | Índice en dos etapas, pesos congelados, estandarización, internet fuera, CAE excluidas del panel largo | aceptada |
| [005](ADR-005-quarto-pages-atlas-ojs.md) | Quarto + Vercel + atlas en Observable JS | aceptada, con adenda |
| [006](ADR-006-notebook-legado-congelado.md) | Notebook legado congelado y reproducción con discrepancias | aceptada |
| [007](ADR-007-crosswalk-por-departamento.md) | Crosswalk nombre a DIVIPOLA por departamento, con overrides | aceptada |
| [008](ADR-008-sfc-en-largo-mapa-bloque-columna.md) | SFC en formato largo con mapa bloque a columna | aceptada |
| [009](ADR-009-empalme-ptgf-kx2f-2021q1.md) | Empalme ptgf/kx2f validado en 2021Q1, con preferencia por kx2f | aceptada |
| [010](ADR-010-desagregacion-temporal-anexo.md) | Desagregación temporal solo como anexo | aceptada |
| [011](ADR-011-uv-quarto-tarball-sin-r.md) | uv + Quarto por tarball, sin R | aceptada |
| [012](ADR-012-datos-derivados-cc-by-sa.md) | Datos derivados bajo CC BY-SA 4.0 | aceptada |
| [013](ADR-013-bogota-separada-y-anm.md) | Bogotá separada y áreas no municipalizadas conservadas | aceptada |
| [014](ADR-014-snowflake.md) | DuckDB como motor, BigQuery en la nube, Snowflake como demo posterior | aceptada, con adendas |
| [015](ADR-015-seleccion-de-variables-del-indice.md) | Selección, normalización y ponderación de las variables del índice | aceptada, con adenda |
| [016](ADR-016-diseno-econometrico.md) | Diseño econométrico del panel departamental | aceptada |
| [017](ADR-017-denominador-del-indice.md) | El denominador de las variables monetarias del índice | aceptada |
| [018](ADR-018-potencia-y-equivalencia.md) | Un nulo se publica con su potencia y su prueba de equivalencia | aceptada |

Las decisiones metodológicas de la versión corregida de la tesis (agosto de 2026) están en [`../decisiones-metodologicas.md`](../decisiones-metodologicas.md) como registro histórico.
