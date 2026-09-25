# Bitácora del agente

Propósito: registrar cada error y cada acierto con su causa raíz y la regla que evita repetirlo. La entrada se escribe antes del arreglo (R-10). Los defectos heredados de la tesis se atribuyen al proceso, nunca a la persona: un proceso sin pruebas produce estos errores en cualquier mano. La bitácora es la memoria del asistente entre sesiones; CLAUDE.md solo guarda las reglas que caben en 40 líneas.

Esquema de una entrada de error:

```
## B-NNN · AAAA-MM-DD · título corto
- Contexto:
- Qué pasó:
- Causa raíz:
- Regla: R-xx (o una regla nueva en una frase) → dónde vive (CLAUDE.md, ADR, prueba)
- Evidencia: archivo::prueba o ruta
- Estado: cerrada | abierta
```

Los aciertos van como `S-NNN` con contexto, qué funcionó, por qué y dónde se reutiliza.

Numeración: B-001 a B-015 son los defectos T-01 a T-15 de la auditoría del notebook consolidado (plan de septiembre de 2026). B-016 en adelante son errores del asistente en esta y en sesiones previas. Los comentarios de `src/iif/legacy/diagnostics.py` citan la numeración de este archivo (Hausman = B-008; Wooldridge = nota dentro de B-011).

---

## Defectos heredados del proceso de la tesis

## B-001 · 2026-09-06 · Dependiente anual repetida en los trimestres
- Contexto: panel legado de 33 departamentos por 14 trimestres (462 filas, 102 columnas). Columnas 7 a 82 (SFC) trimestrales; columnas 85 a 101 (población, internet, educación, IPC, empleo, PIB) anuales.
- Qué pasó: el PIB per cápita y su crecimiento se copiaron en los cuatro trimestres de cada año. La log-diferencia intra-anual es 0 en el 64,3 % de las filas. La dependiente tiene 5 valores por departamento, no 14. N efectivo = 33 × 5 = 165 departamento-años. El modelo "dinámico" regresa la dependiente sobre una copia de sí misma en el 64 % de las filas.
- Causa raíz: el proceso de la tesis unió series trimestrales y anuales por año sin declarar el grano de cada columna. Ninguna prueba comprobaba que la dependiente variara dentro del año.
- Regla: R-05 → CLAUDE.md; ADR-001. El diagnóstico D1 corre en cada reproducción y queda en el libro.
- Evidencia: docs/legacy/reproduccion.md (D1: 1 valor distinto por (departamento, año); fracción de ceros 0,643); src/iif/legacy/variables.py::d1_diagnostics.
- Estado: abierta hasta que exista `mart_panel_departamento_anual` (fase 2). La reproducción conserva el defecto a propósito (ADR-006).

## B-002 · 2026-09-06 · Deflactor de un solo departamento aplicado a los 33
- Contexto: celda 8 del notebook, construcción del índice de precios.
- Qué pasó: `drop_duplicates('anio')` sobre el panel ordenado dejó la primera fila de cada año, que es Amazonas. Ese IPC deflactó a los 33 departamentos.
- Causa raíz: deduplicar por una sola clave cuando la serie es por (departamento, año). Sin prueba de que el deflactor variara entre departamentos.
- Regla: deflactar por unidad, nunca por primera fila; toda deduplicación declara su clave completa → src/iif/legacy/variables.py::VariableOptions(deflator="by_department"); ADR-006.
- Evidencia: src/iif/legacy/variables.py::_ipc_index_first_row (defecto reproducido) y ::_ipc_index_by_department (corrección).
- Estado: cerrada en modo `corrected`; prueba unitaria pendiente en tests/.

## B-003 · 2026-09-06 · Flujo trimestral dividido por PIB anual
- Contexto: ratios de profundidad (microcrédito, consumo y vivienda sobre PIB), celda 8.
- Qué pasó: el numerador es el monto desembolsado en el trimestre; el denominador es PIB per cápita anual por población. La ratio queda dividida por cuatro y mezcla dos granos.
- Causa raíz: sin regla de anualización por variable (stock frente a flujo).
- Regla: cada variable declara si es stock o flujo y su regla de anualización (flujo: suma de 4 trimestres exigiendo 4; stock: valor de Q4) → dbt/seeds/dim_variable.csv (fase 1); ADR-001; ADR-008.
- Evidencia: src/iif/legacy/variables.py (`flow_scale = 4.0` en modo `corrected` es solo una aproximación).
- Estado: abierta hasta `fct_inclusion_departamento_anual`.

## B-004 · 2026-09-06 · Internet igual a cero en 50 observaciones
- Contexto: columna 89 `Conexión a internet %`; Bogotá 2017 y 2018 con 0 %.
- Qué pasó: 50 filas con cero exacto entraron al PCA como cobertura nula. Bogotá es la unidad con más internet del país.
- Causa raíz: faltantes codificados como cero en la fuente y sin prueba de rango plausible.
- Regla: R-13 (los ceros de SFC y MEN son faltantes; en MinTIC la ausencia es NULL) → CLAUDE.md; src/iif/legacy/variables.py::VariableOptions(internet_zero_is_missing=True).
- Evidencia: docs/legacy/reproduccion.md (descriptivas: `d_acc_internet` min = 0); data/legacy/diccionario_panel_legacy.csv, fila 89.
- Estado: cerrada en modo `corrected`; prueba pandera de rango pendiente.

## B-005 · 2026-09-06 · Pesos implícitos nunca publicados; microcrédito con signo negativo
- Contexto: índice por PCA, celda 9; 4 componentes por la regla del 80 % de varianza acumulada.
- Qué pasó: el índice es una combinación lineal de las 9 variables. Los pesos implícitos (peso del componente por carga) dan microcrédito/PIB = −0,231 y transferencias = −0,006. Más microcrédito baja el índice. El notebook nunca los imprimió. Kaiser retendría 3 componentes, no 4: PC4 tiene eigenvalor menor que 1 y carga −0,66 en internet.
- Causa raíz: la regla de retención se eligió sin mirar la interpretación; no había prueba de signo por variable.
- Regla: los pesos implícitos por variable se publican siempre y se prueba que cada variable de inclusión entre con signo no negativo → ADR-004; src/iif/legacy/index.py::IndexResult.implied_weights.
- Evidencia: docs/legacy/reproduccion.md, tabla "Pesos implícitos por variable".
- Estado: cerrada (publicados); el índice en dos etapas es fase 2.

## B-006 · 2026-09-06 · Min-max tras PCA más EPS
- Contexto: celda 9, escalado del índice a [0, 1] con `EPS = 1e-4`.
- Qué pasó: el mínimo del índice vale 0,0001 y `log(IIF)` = −9,21 en esa fila, frente a una media de −1,3. Un outlier de 9,8 desviaciones creado por el escalado, no por los datos.
- Causa raíz: llevar un score centrado a [0, 1] y luego tomar logaritmo.
- Regla: estandarizar, no min-max; sin logaritmo de un índice acotado en cero → ADR-004; src/iif/legacy/index.py (`scale="standardize"`).
- Evidencia: docs/legacy/reproduccion.md (descriptivas: `IIF` min 0,0001; `log_IIF` min −9,2103).
- Estado: cerrada como opción; será el valor por defecto del índice nuevo.

## B-007 · 2026-09-06 · Orientación de signo forzada y verificada de forma circular
- Contexto: celda 9; cada componente se voltea si correlaciona negativo con cuentas de ahorro.
- Qué pasó: tras voltear, el notebook "verifica" que corr(IIF, cuentas) = 0,87 > 0. La prueba no puede fallar.
- Causa raíz: la comprobación usa la misma variable que fija el signo.
- Regla: la orientación se fija a priori (cada variable codificada como "más = más inclusión") y la prueba es de signo de los pesos implícitos, no de correlación con la referencia → ADR-004.
- Evidencia: src/iif/legacy/index.py (bucle sobre `sign_ref`); docs/legacy/reproduccion.md ("Corr orientación IIF~cuentas").
- Estado: abierta (fase 2).

## B-008 · 2026-09-06 · Hausman con covarianza clusterizada
- Contexto: celda 17.
- Qué pasó: FE y RE se estimaron con covarianza clusterizada; la diferencia de matrices no es definida positiva y `pinv` devuelve un número arbitrario. Reproducción: χ² = 292,8; documento: 33,9.
- Causa raíz: aplicar la fórmula clásica de Hausman a covarianzas robustas.
- Regla: nunca Hausman con covarianza robusta; usar Mundlak → src/iif/legacy/diagnostics.py::hausman_clustered (avisa "no válido") y ::mundlak.
- Evidencia: docs/legacy/reproduccion.md ("Hausman (NO válido con cov clusterizada)").
- Estado: cerrada.

## B-009 · 2026-09-06 · Modelos regionales con 4 clústeres
- Contexto: celda 20, heterogeneidad por región.
- Qué pasó: Pacífica y Orinoquía se estimaron con 4 departamentos; Amazonía con 6. La inferencia clusterizada con menos de 10 grupos no es fiable y los p-valores publicados no dicen lo que parecen.
- Causa raíz: submuestrar en vez de interactuar.
- Regla: heterogeneidad por interacciones sobre el panel completo y wild cluster bootstrap; aviso automático con menos de 10 clústeres → src/iif/legacy/panel.py::fit_fe; ADR de econometría pendiente (fase 3).
- Evidencia: docs/legacy/reproduccion.md ("Heterogeneidad regional": N_dep 4, 4 y 6).
- Estado: cerrada el aviso; abierta la estimación (fase 3).

## B-010 · 2026-09-06 · Recorte y winsorización después de los rezagos, sobre la dependiente pooled
- Contexto: celda 19, robustez.
- Qué pasó: los cuantiles 1 % y 5 % se calcularon sobre `crec_pib` de todo el panel ya rezagado. Recortar filas después de rezagar rompe la secuencia temporal de cada departamento; los cuantiles pooled mezclan 2020 con años normales.
- Causa raíz: robustez añadida al final, sin rehacer el panel.
- Regla: cualquier recorte se aplica antes de construir rezagos y se documenta por unidad → modo `corrected` (pendiente de implementar).
- Evidencia: src/iif/legacy/pipeline.py (filas `Trimming 1%` y `Winsorización 5%` sobre `pm`).
- Estado: abierta.

## B-011 · 2026-09-06 · Nickell con el T del panel y fórmula de AR(1) puro; β nunca corregido
- Contexto: celda 18.
- Qué pasó: sesgo ≈ −(1+ρ)/(T−1) con T = 14 trimestres, cuando la dependiente tiene 5 valores anuales. La fórmula supone AR(1) sin regresores. El ρ corregido se calculó y no se usó en ninguna estimación. El documento afirma "sesgo cuantificado" con ρ̂ = 0,4279 del modelo agregado. Nota relacionada: el notebook llama "Wooldridge" a una correlación de residuos con su rezago; no es la prueba de Wooldridge (src/iif/legacy/diagnostics.py::residual_ar1).
- Causa raíz: aplicar una fórmula de libro sin comprobar sus supuestos ni el T efectivo.
- Regla: Nickell se calcula con el T efectivo de la dependiente y se presenta solo como orientación; si se corrige, se corrige la estimación → src/iif/legacy/diagnostics.py::nickell_bias (docstring); reestimación anual en ADR-001.
- Evidencia: docs/legacy/reproduccion.md ("Nickell"); src/iif/legacy/pipeline.py (`T = pm.index.get_level_values(1).nunique()`).
- Estado: abierta (fase 3).

## B-012 · 2026-09-06 · Umbral urbano/rural sobre 462 filas replicadas; variable muerta
- Contexto: celda 8.
- Qué pasó: el cuantil 75 de la densidad se tomó sobre 462 filas (cada departamento 14 veces) en vez de sobre 33 departamentos. Antioquia quedó "rural". La variable `urbano` no entra en ningún modelo.
- Causa raíz: estadísticos de unidad calculados sobre filas replicadas.
- Regla: umbrales y cuantiles de unidad se calculan sobre unidades → src/iif/legacy/variables.py::VariableOptions(urban_threshold_over="departments").
- Evidencia: src/iif/legacy/variables.py::build_variables (`umbral`).
- Estado: cerrada en modo `corrected`; la variable sigue sin uso.

## B-013 · 2026-09-06 · Rename map con claves rotas; 81 de 102 columnas sin usar
- Contexto: celda 4 y el xlsx.
- Qué pasó: tres claves del mapa (`NRO CORRESPONSALES TOTALES`, `Key` y `MONTO CREDITO CONSUMO  HOMBRES` con doble espacio) no coinciden con ninguna cabecera; pandas renombra en silencio. El notebook usa 21 columnas de 102. Quedan fuera las cuentas de ahorro electrónicas, el proxy fintech más directo, y todas las series por género.
- Causa raíz: mapa manual sin prueba de cobertura; sin diccionario de datos.
- Regla: R-15 (una fuente de verdad por constante) y prueba de que cada clave de un mapa existe en los datos → dbt/seeds/dim_variable.csv (fase 1); data/legacy/diccionario_panel_legacy.csv, columna `usada_por_notebook`.
- Evidencia: src/iif/legacy/constants.py::RENAME_MAP (comentario de cabecera) y ::USED_RAW_COLUMNS (21 columnas).
- Estado: cerrada (documentado); las columnas nuevas entran con el índice de fase 2.

## B-014 · 2026-09-06 · El documento no reproduce desde el notebook
- Contexto: celdas 4 y 22 (constantes DOC y DOC_OTROS); Tabla 6 del documento.
- Qué pasó: 40 filas en el libro de verificación, 25 discrepancias. Todas las N de la Tabla 6 difieren en exactamente 33 (una sección transversal). 6 de 8 β difieren. El SE de B2 es una errata (texto 5,96; tabla 9,5553). 13 de las 26 cifras guardadas en el notebook nunca se comparan; una comparación manual muestra que al menos 7 de ellas también difieren, así que el total real ronda 32. El código que produjo el documento no está en la subida.
- Causa raíz: el documento se escribió con una versión del panel o del código distinta de la consolidada y sin libro de verificación automático.
- Regla: R-09 (toda cifra publicada traza a prueba, libro o test dbt) → CLAUDE.md; config/tesis_documento.yaml es la única copia de las cifras del documento.
- Evidencia: docs/legacy/reproduccion.md ("Verificación contra el documento", TOTAL 25); src/iif/legacy/ledger.py.
- Estado: cerrada (publicado). Abierta: extender el libro a las 13 cifras sin comparar.

## B-015 · 2026-09-06 · Rutas y metadatos personales en los artefactos
- Contexto: celdas 3 y 23 del notebook; `docProps/core.xml` y `xl/workbook.xml` del xlsx.
- Qué pasó: rutas absolutas de dos máquinas del autor (Linux y Windows), nombre legal completo del autor en las propiedades del libro, kernelspec malformado y nombres de notebooks predecesores en la celda 0.
- Causa raíz: archivos guardados desde la máquina personal sin paso de limpieza.
- Regla: R-04 y R-08 → CLAUDE.md; src/iif/data/scrub.py::find_private_strings corre en `iif scrub` y falla si queda algo.
- Evidencia: data/legacy/SHA256SUMS; src/iif/data/scrub.py::PRIVATE_PATH_PATTERNS.
- Estado: cerrada.

## B-031 · 2026-09-06 · Doble conteo: el panel de la tesis suma municipios y total departamental
- Contexto: S13, reconstrucción de las nueve variables SFC del panel legado desde `ptgf-ywrb` (603.232 filas, 2017Q4 a 2021Q1).
- Qué pasó: para las 462 filas y las nueve variables, el valor del panel es exactamente la suma de todas las filas de `ptgf` por (departamento, trimestre, `tipo`), incluida la fila de total departamental (`renglon = 999`). Como esa fila es la suma de las municipales, cada nivel SFC del panel (corresponsales, depósitos, pagos, transferencias, cuentas, montos de crédito) vale el doble del real. La razón panel/real es 2,000000 en todas las filas no nulas. Antioquia 2018Q1: 7.961.768 depósitos en el panel, 3.980.884 en la fuente.
- Causa raíz: agregación con `groupby(departamento, trimestre).sum()` sin filtrar `renglon = 999`. Ninguna prueba comparaba el panel con la fuente.
- Consecuencias: las log-diferencias, la estandarización y el PCA no cambian (factor constante); las razones flujo/PIB de profundidad y los niveles per cápita están al doble; T-03 se agrava. Se añade como T-16 a la auditoría.
- Regla: todo agregado desde la SFC filtra `renglon = 999` (total departamental) o suma solo filas municipales, nunca ambas; la prueba de reconstrucción corre con `make test-data` → tests/test_legacy_vs_ptgf.py; ADR-008.
- Evidencia: tests/test_legacy_vs_ptgf.py::test_legacy_equals_twice_the_true_total (9 variables); ::test_department_totals_equal_municipal_sums.
- Estado: cerrada en el almacén (el modo `corrected` de la reproducción y los marts usan el total real); abierta en el documento de la tesis, que no se reescribe.

---

## Errores del asistente

## B-016 · 2026-09-06 · Notificaciones de subagentes perdidas
- Contexto: esta sesión; auditoría del notebook con varios subagentes en paralelo.
- Qué pasó: dos subagentes terminaron y la notificación de fin no llegó. El asistente siguió esperando y después asumió que no habían terminado.
- Causa raíz: fiarse de la notificación como única señal de fin.
- Regla: comprobar las transcripciones de los subagentes por `mtime` antes de esperar o relanzar; nunca asumir → esta bitácora (regla operativa del asistente).
- Evidencia: esta sesión (transcripción).
- Estado: cerrada.

## B-017 · 2026-09-06 · `pkill -f` mató la propia shell dos veces
- Contexto: reinicio de un servidor de desarrollo desde Bash.
- Qué pasó: `pkill -f "<patrón>"` coincidió con la línea de comando de la propia shell, que contiene el patrón, y la mató. Ocurrió dos veces.
- Causa raíz: `-f` compara contra la línea de comando completa, incluida la del comando que lo invoca.
- Regla: `pgrep -f "[n]ext-server"` (el corchete impide que el patrón se encuentre a sí mismo) y `kill` por PID → esta bitácora.
- Evidencia: esta sesión (transcripción).
- Estado: cerrada.

## B-018 · 2026-09-06 · Captura de pantalla de más de 8.000 px rechazada
- Contexto: revisión visual de una página larga.
- Qué pasó: enviar una captura de página completa, de más de 8.000 px de alto, falló con HTTP 400 dos veces.
- Causa raíz: límite de tamaño de imagen del canal.
- Regla: recortar capturas a 4.000 px o menos por archivo; varias capturas antes que una gigante → esta bitácora.
- Evidencia: esta sesión (transcripción).
- Estado: cerrada.

## B-019 · 2026-09-06 · Cifras copiadas de comentarios obsoletos
- Contexto: otro repositorio del autor (modelo semántico TMDL y su README), sesión previa.
- Qué pasó: se citaron 1.347 variantes y 45 activos tomados de comentarios; los datos tenían 1.392 y 48.
- Causa raíz: los comentarios no se actualizan con los datos.
- Regla: contar desde los datos (`.length`, `count(*)`), nunca desde comentarios ni READMEs. Es el mismo principio que R-09 → CLAUDE.md R-09 y esta bitácora.
- Evidencia: sesión previa (transcripción).
- Estado: cerrada.

## B-020 · 2026-09-06 · CI en rojo durante dos semanas sin que nadie lo viera
- Contexto: otro repositorio del autor (pipeline de datos), sesión previa.
- Qué pasó: los commits con `[skip ci]` ocultaron que la rama principal llevaba dos semanas en rojo. Las pruebas dependían de una variable de entorno local.
- Causa raíz: pruebas con estado implícito y CI saltado por conveniencia.
- Regla: las pruebas fijan su propio entorno; nada visible en CI depende de un secreto del desarrollador; `[skip ci]` no se usa → ADR-014 (el job Snowflake se condiciona a los secrets; el job DuckDB nunca); .github/workflows/ci.yml (S7).
- Evidencia: sesión previa (transcripción).
- Estado: cerrada.

## B-021 · 2026-09-06 · `git add exports/*.json` no recursivo
- Contexto: otro repositorio del autor, sesión previa.
- Qué pasó: el glob no entró en subcarpetas; 48 archivos quedaron fuera del repo durante 18 días sin error alguno.
- Causa raíz: glob de shell no recursivo y ausencia de prueba de que lo exportado esté versionado.
- Regla: `git add -A <dir>/` y una prueba que compare lo esperado contra `git ls-files` → esta bitácora; `iif manifest verify` cumple ese papel para data/raw (S9).
- Evidencia: sesión previa (transcripción).
- Estado: cerrada.

## B-022 · 2026-09-06 · Instalación editable antes de que existiera el paquete
- Contexto: esta sesión, paso S1.
- Qué pasó: `uv sync` corrió con `src/iif/` vacío; el paquete quedó instalado sin módulos e `import iif` fallaba.
- Causa raíz: hatchling empaqueta lo que existe en el momento de la instalación.
- Regla: crear `src/<pkg>/__init__.py` antes de `uv sync`, o `uv sync --reinstall-package iif` después → esta bitácora; Makefile `setup`.
- Evidencia: src/iif/__init__.py; pyproject.toml (`packages = ["src/iif"]`).
- Estado: cerrada.

## B-023 · 2026-09-06 · TerriData y la API de GitHub no accesibles; `gh` ausente
- Contexto: esta sesión; verificación de fuentes e instalación de herramientas.
- Qué pasó: `ddtspr.dnp.gov.co` (DNP TerriData) no responde a través del proxy. La API REST de GitHub devuelve error y `gh` no está instalado, así que no se pueden subir Release assets desde la sesión. Los tarballs de Releases sí descargan.
- Causa raíz: restricciones del proxy de la sesión.
- Regla: TerriData queda descartada como fuente (además no tiene API); los Release assets los sube el autor desde el navegador; Quarto y tectonic se instalan por tarball → scripts/install_quarto.sh; ADR-003; ADR-011.
- Evidencia: scripts/install_quarto.sh (comentario de cabecera).
- Estado: cerrada.

---

## B-024 · 2026-09-06 · El MapServer del MGN devuelve geometría nula en todos los rasgos
- Contexto: descarga de las capas Departamento (319) y Municipio (317) del MGN 2024 por ArcGIS REST, `f=geojson`, `returnGeometry=true`.
- Qué pasó: la primera descarga terminó "bien" (33 y 1.121 rasgos, 0,01 y 0,35 MB) y los dos GeoJSON tenían `geometry: null` en cada rasgo. Ninguna variante de parámetros del `MapServer` (outSR, precisión, bbox, objectIds, quantization) devolvió polígonos. El `FeatureServer` del mismo servicio, con la misma numeración de capas, sí los devuelve.
- Causa raíz: el código daba por buena cualquier respuesta con rasgos y no comprobaba la geometría. El tamaño (10 KB para 33 departamentos) era la señal y no se miró.
- Regla: un descargador falla si la primera página trae rasgos sin geometría; el tamaño esperado se anota en `config/sources.yaml` y una descarga muy por debajo es sospechosa → `src/iif/acquire/mgn.py`.
- Evidencia: tests/test_acquire.py::test_mgn_null_geometry_is_an_error; `data/raw/mgn/*.geojson` (1,6 y 4,9 MB tras el arreglo).
- Estado: cerrada.

## B-025 · 2026-09-06 · `ptgf` en una sola partición `anio=sin_fecha` y 82 columnas numéricas como texto
- Contexto: primera descarga de `sfc-ptgf-ywrb` (603.232 filas).
- Qué pasó: `config/sources.yaml` copió de `kx2f` la columna de partición `fecha_corte` y una expresión regular para tipar; en `ptgf` la columna se llama `fechacorte` y las cantidades no empiezan por `nro|saldo|...`. El descargador escribió todo en `anio=sin_fecha` con las 82 cantidades como texto y no avisó.
- Causa raíz: nombres de columna supuestos en vez de leídos de los metadatos de Socrata; una columna de partición ausente se trataba como "sin fecha" en lugar de como error.
- Regla: el tipado sale de `api/views/<id>.json` (`number`, `calendar_date`) y los códigos se declaran en `code_cols`; una columna de partición inexistente es un error → `src/iif/acquire/soda.py::typing_from_metadata`.
- Evidencia: tests/test_acquire.py::test_typing_from_metadata_keeps_codes_as_text, ::test_soda_unknown_partition_column_raises; manifiesto con 5 particiones de `ptgf` (2017 a 2021).
- Estado: cerrada.

## B-026 · 2026-09-06 · `pivot_table(dropna=False)` agotó la memoria dos veces
- Contexto: parser del valor agregado departamental por actividad (10.395 filas de salida).
- Qué pasó: el proceso murió por el OOM killer con 12,7 GB de RSS; la segunda vez con `ulimit -v` falló con un `malloc` de 3 GB. `pivot_table(..., dropna=False)` sobre siete niveles de índice construye el producto cartesiano de todos los valores de cada nivel, no las combinaciones observadas.
- Causa raíz: opción copiada sin conocer su semántica; el primer fallo se atribuyó a otra causa (descarga concurrente) sin leer `dmesg`.
- Regla: ensanchar con `set_index(...).unstack()` sobre combinaciones observadas; correr parsers nuevos bajo `ulimit -v`; ante un exit 137, leer `dmesg` antes de suponer → `src/iif/parse/dane.py::_widen`.
- Evidencia: tests/test_parse.py::test_widen_uses_observed_combinations_only; `dmesg`: "Memory cgroup out of memory: Killed process (iif) anon-rss:12773176kB".
- Estado: cerrada.

## B-027 · 2026-09-06 · `mpio_ccdgo` del MGN tiene 3 dígitos
- Contexto: atributos de la capa Municipio del MGN 2024.
- Qué pasó: la validación de unicidad de `mpio_ccdgo` falló con 823 duplicados: en el MGN ese campo es el código municipal dentro del departamento (3 dígitos) y el DIVIPOLA de 5 es `mpio_cdpmp`.
- Causa raíz: se supuso el nombre del campo por analogía con las tablas del DANE.
- Regla: todo código geográfico se valida por ancho (`^\d{2}$`, `^\d{5}$`) y por prefijo (`left(mpio, 2) = dpto`) en pandera y en dbt → `src/iif/parse/mgn.py`.
- Evidencia: tests/test_parse.py::test_mgn_interim_matches_dane_codes.
- Estado: cerrada.

## B-028 · 2026-09-06 · El subagente de dbt murió por el límite de sesión
- Contexto: dos subagentes en paralelo (documentos y dbt) mientras el hilo principal descargaba y escribía código.
- Qué pasó: el agente de dbt terminó con HTTP 429 ("session limit") mientras iteraba una macro. Sus archivos estaban en disco y `dbt build` pasó (127 de 127) al reejecutarlo desde el hilo principal.
- Causa raíz: el consumo de tres procesos en paralelo contra un límite compartido.
- Regla: cerca del límite, un solo hilo de trabajo; antes de dar por perdido el trabajo de un agente, comprobar el disco y reejecutar la verificación (complementa B-016).
- Evidencia: transcripción del agente; `dbt build --profiles-dir dbt --project-dir dbt` en cero.
- Estado: cerrada.

## B-029 · 2026-09-06 · Rutas de Quarto relativas al documento
- Contexto: primer `quarto render` del sitio completo.
- Qué pasó: `{{< include docs/LICENCIAS_DATOS.md >}}` en `datos/fuentes.qmd` buscó `datos/docs/...`; además tres páginas fijaban `IIF_ROOT` con `os.getcwd()`, que en Quarto es el directorio del documento, no la raíz.
- Causa raíz: las directivas `include` se resuelven desde el `.qmd` que las contiene; el cwd de ejecución depende de `execute-dir`.
- Regla: `execute-dir: project` en `_quarto.yml`; nunca fijar `IIF_ROOT` desde un `.qmd` (el paquete encuentra la raíz por `pyproject.toml`); includes con ruta relativa al documento → `_quarto.yml`, `datos/fuentes.qmd`.
- Evidencia: `quarto render` en cero; `_site/datos/fuentes.html` contiene la tabla del manifiesto.
- Estado: cerrada.

## B-030 · 2026-09-06 · Workflow de CI con YAML inválido a punto de subirse
- Contexto: `.github/workflows/ci.yml` escrito a mano; `make check` no lo validaba.
- Qué pasó: un `run: echo "Sin SNOWFLAKE_ACCOUNT: se omite ..."` con dos puntos y espacio dentro de un escalar sin comillas rompía el YAML. GitHub habría rechazado el workflow en el primer push.
- Causa raíz: el archivo se validó "a ojo"; ninguna prueba lo cargaba.
- Regla: `make lint` y `tests/test_repo.py` cargan todos los workflows con `yaml.safe_load` → Makefile, tests/test_repo.py.
- Evidencia: tests/test_repo.py::test_workflows_are_valid_yaml_with_jobs.
- Estado: cerrada.

## B-032 · 2026-09-06 · En `kx2f` el total departamental no siempre es la suma de los municipios
- Contexto: prueba `assert_sfc_geo_totals_equal_municipal_sums` extendida a `kx2f` (S12).
- Qué pasó: 274 combinaciones (corte, departamento, bloque, columna) difieren: hasta 2,2 % en el bloque de corresponsales físicos desde 2022Q3 (`_2_`, `_3_`, `_4_`, `_80_`) y menos de 0,13 % en transacciones. En `ptgf` la igualdad es exacta.
- Causa raíz: no está en el código; es la fuente. La fila 999 la reporta la entidad y no siempre cuadra con sus filas municipales (corresponsales contados en más de un municipio o reasignados).
- Regla: la tolerancia es por fuente y vive en `dbt_project.yml` (`sfc_total_tol_ptgf` 1e-6, `sfc_total_tol_kx2f` 3 %); los marts departamentales usan la fila 999 y los municipales la suma, y la diferencia se publica, no se oculta.
- Evidencia: dbt/tests/assert_sfc_geo_totals_equal_municipal_sums.sql; dbt/dbt_project.yml.
- Estado: cerrada (documentada); abierta como pregunta a la SFC.

## B-033 · 2026-09-06 · Primeros números del empalme ptgf/kx2f en 2021Q1
- Contexto: ADR-009 exigía anotar las diferencias antes de fijar umbrales.
- Qué pasó: con la correspondencia posicional de 70 columnas (`xw_sfc_columns_empalme`) y los totales departamentales de 2021Q1: 2.052 pares con dato en ambas tablas; mediana global de la diferencia relativa 0,02 %; por bloque, cuentas de ahorro 0,02 %, transacciones 0,02 %, crédito de consumo 0,2 %, vivienda 0,65 %, corresponsales físicos 3,4 % (p90 10 %, máximo 31,5 %), microcrédito mediana 0 pero p90 de 12 % a 13 % y máximo 40 % (Huila, Nariño, Santander en el rango hasta 1 SMMLV). 103 pares de 2.052 (5 %) difieren más del 10 %. Peores departamentos por mediana: Antioquia 1,8 %, Bogotá 1,65 %, Atlántico 1,6 %. Las cuentas de ahorro electrónicas (8 columnas) no existen en `kx2f`.
- Causa raíz: `kx2f` es una serie revisada por las entidades; las diferencias grandes se concentran en microcrédito por rango y en corresponsales propios, no en saldos ni transacciones.
- Regla: umbral de la prueba = mediana por departamento ≤ 2 % (pasa con margen); las diferencias por bloque se publican en `datos/crosswalk.qmd`; los marts prefieren `kx2f` en 2021Q1 y guardan la diferencia (ADR-009).
- Evidencia: dbt/tests/assert_sfc_empalme_2021q1.sql; data/interim/sfc/empalme_2021q1_departamento.csv.
- Estado: cerrada.

## B-034 · 2026-09-06 · El repositorio publicaba resultados de la tesis como si fueran del proyecto
- Contexto: el autor pidió desde el inicio que la tesis fuera el borrador del proyecto nuevo. El README y el sitio quedaron llenos de sus cifras (β, p, N, KMO, tabla de discrepancias, diagnósticos).
- Qué pasó: se interpretó "reproducción honesta" como "publicar la tesis auditada". El resultado leído por un tercero era el de la tesis, no el del proyecto; además fijaba como conclusión algo que el proyecto todavía no ha estimado.
- Causa raíz: se confundió el insumo (el trabajo de grado y su auditoría) con el producto (los resultados nuevos). La instrucción original decía "expansión de dominio", no "publicación de la tesis".
- Regla: ninguna cifra del trabajo de grado aparece en README, sitio o portafolio como resultado. Los artefactos legados son insumo congelado y evidencia de esta bitácora; `src/iif/legacy/` es auditoría interna. Las secciones de resultado dicen "todavía no hay" hasta que la fase 3 los produzca → ADR-006 (adenda), README, `_quarto.yml`.
- Evidencia: ADR-006 adenda; `_quarto.yml` sin `reproduccion-tesis.qmd`; README con `#main-result` vacío y explícito.
- Estado: cerrada.

## B-035 · 2026-09-06 · Dos plataformas de despliegue para un solo autor
- Contexto: el sitio del proyecto se configuró en GitHub Pages mientras el portafolio del autor ya vivía en Vercel.
- Qué pasó: el autor tuvo que preguntar qué era Pages. Se le pedía activar y mantener una segunda plataforma sin ninguna ventaja.
- Causa raíz: se eligió Pages por costumbre (repositorio de GitHub → Pages) sin mirar dónde despliega ya el autor.
- Regla: antes de elegir plataforma, mirar qué usa el autor. El sitio va a Vercel; como Vercel no compila Quarto ni Python, CI renderiza y empuja `_site` a la rama `site`, y Vercel despliega esa rama → ADR-005 (adenda), `.github/workflows/ci.yml`.
- Evidencia: `.github/workflows/ci.yml` (paso "Publicar la rama site"); `vercel.json` en `main` con `ignoreCommand`.
- Estado: cerrada.

## B-036 · 2026-09-06 · Se dio por descartado BigQuery sobre una instrucción ambigua
- Contexto: el autor escribió "dejemos google bigquery y la otra tecnología que mencionaste por ahora y snowflake como un demo a posterior".
- Qué pasó: se leyó "dejemos X por ahora" como "dejemos X de lado" y se escribió una adenda a ADR-014 descartando BigQuery y Databricks. El autor aclaró en el mismo turno que sí quería BigQuery implementado.
- Causa raíz: la frase admite las dos lecturas opuestas (dejar de lado / conservar) y se resolvió sin preguntar, en una decisión de arquitectura que ya se había discutido antes.
- Regla: una instrucción con dos lecturas opuestas sobre una decisión de valor se pregunta, no se resuelve por contexto; el coste de una pregunta es menor que el de un ADR equivocado (R-11).
- Evidencia: ADR-014, adendas 1 y 2; `bigquery/`.
- Estado: cerrada.

## B-037 · 2026-09-06 · Una semilla con esquema nuevo no se recarga sola
- Contexto: `dim_variable` pasó de 10 a 12 columnas al generarse el diccionario completo.
- Qué pasó: `dbt seed` falló con "Error when sniffing file": dbt hace `COPY` sobre la tabla existente, que conserva el esquema viejo, y el mensaje culpa al CSV en vez de al esquema. Se perdió tiempo revisando comillas y separadores del archivo, que estaba bien.
- Causa raíz: dbt no recrea una semilla cuando cambian sus columnas, salvo con `--full-refresh`.
- Regla: al cambiar las columnas de una semilla, `dbt seed --select <semilla> --full-refresh`; si un error de CSV menciona un número de columnas distinto al del archivo, el problema es la tabla destino → `docs/GUIA_DEL_PROYECTO.md` (sección 8).
- Evidencia: `dbt/seeds/dim_variable.csv` con 12 columnas; el error citaba 10.
- Estado: cerrada.

## B-038 · 2026-09-06 · El PCA por dimensión iba a repetir el defecto del índice auditado
- Contexto: ADR-015 fijó un componente principal por dimensión como método del índice nuevo, por analogía con la literatura y con el índice del trabajo de grado.
- Qué pasó: al estimarlo, el KMO salió 0,314 en uso y 0,404 en profundidad (por debajo de 0,5 las variables no comparten varianza común suficiente) y el primer componente dio peso implícito **negativo** al microcrédito y al monto de transacciones. Es exactamente el defecto B-005: una variable que debería sumar entrando restando.
- Causa raíz: se eligió el método antes de medir si sus supuestos se cumplían. El ADR se escribió con el método ya decidido en vez de dejarlo abierto a la medición.
- Regla: R-17. Antes de fijar un método se mide su supuesto y la medición se publica; el índice publica siempre sus pesos implícitos y una prueba falla si alguno es negativo → CLAUDE.md, ADR-015 (adenda), `tests/test_index.py::test_pesos_implicitos_nunca_negativos`.
- Evidencia: `data/processed/indice_diagnosticos.csv` (KMO por dimensión); `metodologia/indice.qmd` publica la tabla.
- Estado: cerrada. El método publicado son pesos iguales dentro de cada dimensión; el componente principal queda como sensibilidad, con correlación de rangos 0,96 frente al publicado.

## B-039 · 2026-09-06 · El mapa salía como un rectángulo de color: el sentido de giro de los anillos
- Contexto: primera versión del atlas, coropleta de departamentos con d3 y TopoJSON sobre la geometría del MGN 2024.
- Qué pasó: el mapa se dibujaba como un rectángulo azul que ocupaba todo el lienzo, con Colombia reducida a una mancha de diez píxeles en el centro. Los datos exportados eran correctos: 33 rasgos, códigos completos, límites en lon [−81,7; −66,8] y lat [−4,2; 13,4].
- Causa raíz: **TopoJSON y la geometría esférica de d3 esperan el anillo exterior en sentido horario, que es el contrario del que pide RFC 7946 para GeoJSON.** Con el giro de RFC, d3 interpreta cada anillo como el complemento del polígono. Medido con la propia d3: `d3.geoArea` de Bogotá daba 12,566, es decir 4π, la esfera entera; la suma de los 33 departamentos daba 590 estereorradianes cuando la esfera mide 12,57. Al ajustar la proyección a ese contorno, todo lo demás se encogía.
- Se agravaba con un segundo defecto: una isla de Bolívar (que tiene 51 polígonos) colapsaba a un anillo de área cero al simplificar, y un anillo degenerado produce el mismo efecto.
- Cómo se encontró: no mirando el código, sino midiendo. Primero el área con signo de cada anillo en Python, después `d3.geoArea` en el navegador, que fue la que dio el número imposible.
- Regla: la geometría publicada se valida contra una cantidad física conocida antes de darla por buena. La suma de las áreas esféricas de los departamentos tiene que dar el área de Colombia: 0,0281 estereorradianes. Ahora da 0,02817.
- Evidencia: `src/iif/export/atlas.py::_limpiar` (giro horario y descarte de islas por debajo de la resolución, con el conteo publicado en `atlas_meta.json`).
- Estado: cerrada.

---

## Aciertos

## S-001 · 2026-09-06 · Paginación SODA por `$order=:id`
- Contexto: descarga de las tablas de SFC, MinTIC y MEN en datos.gov.co.
- Qué funcionó: `$order=:id&$limit=50000&$offset=n` da páginas estables y completas; el total coincide con `count(*)`. Sin `$order`, Socrata puede repetir o saltar filas entre páginas.
- Dónde se reutiliza: src/iif/acquire/soda.py (S9); config/sources.yaml.

## S-002 · 2026-09-06 · 2021Q1 existe en las dos tablas de la SFC
- Contexto: `ptgf-ywrb` termina en 2021Q1 y `kx2f-xjdq` empieza en 2021Q1.
- Qué funcionó: ese trimestre es una prueba natural del empalme: mismas entidades, mismos municipios, dos esquemas. Las diferencias por departamento y variable se miden antes de fijar umbrales.
- Dónde se reutiliza: ADR-009; prueba singular de dbt para el empalme (S12).

## S-003 · 2026-09-06 · `Last-Modified` del DANE sirve para nombrar vintages
- Contexto: los XLSX del DANE se revisan cada julio y la URL no cambia.
- Qué funcionó: el servidor responde a HEAD con `Last-Modified` (PIB departamental: 2026-07-03). El sufijo `__lmYYYYMMDD` e `If-Modified-Since` evitan descargas repetidas y fechan cada revisión.
- Dónde se reutiliza: src/iif/acquire/dane.py (S9); ADR-002 (`dim_vintage.source_updated_at`).

## S-004 · 2026-09-06 · MGN 2024 por ArcGIS REST devuelve GeoJSON con DIVIPOLA
- Contexto: la página oficial de descarga del MGN da 404.
- Qué funcionó: el servicio REST del DANE responde con `f=geojson`, 2.000 registros por página con `resultOffset`, y trae `dpto_ccdgo` y `mpio_ccdgo`. Admite `geometryPrecision` y `maxAllowableOffset` para simplificar.
- Dónde se reutiliza: src/iif/acquire/mgn.py (S9); ADR-007 (crosswalk); ADR-005 (TopoJSON del atlas).

## S-005 · 2026-09-06 · La reproducción coincide con el notebook a 1,4e-6
- Contexto: port del notebook consolidado a src/iif/legacy con pandas 3 (el notebook corrió con pandas 1.5.3).
- Qué funcionó: 39 cifras del dump del notebook (docs/legacy/RESULTADOS_CONSOLIDADO_2.md) se reproducen con diferencia máxima 1,4e-6 y el mismo conteo de discrepancias frente al documento (25). El port es fiel; las discrepancias son del documento, no del port.
- Dónde se reutiliza: docs/legacy/reproduccion.md; pruebas doradas en tests/ (pendientes de escribir con estos valores).

## S-006 · 2026-09-06 · Quarto y tectonic por tarball a través del proxy
- Contexto: la API de GitHub está bloqueada y `gh` no existe (B-023).
- Qué funcionó: `github.com/<org>/<repo>/releases/download/<tag>/<archivo>.tar.gz` descarga sin problema. Quarto 1.7.32 y tectonic se instalan en `~/.local/opt` sin `gh`, sin `apt` y sin R.
- Dónde se reutiliza: scripts/install_quarto.sh; Makefile `quarto-install`; ADR-011.

## S-007 · 2026-09-06 · `FeatureServer` con `maxAllowableOffset` deja el MGN en pocos MB
- Contexto: B-024. Cinco departamentos sin simplificar pesaban 0,7 MB por rasgo.
- Qué funcionó: `maxAllowableOffset` 0,0005° (~55 m) deja los 33 departamentos en 1,6 MB y 0,001° (~110 m) los 1.121 municipios en 4,9 MB, con `geometryPrecision: 4`. Suficiente para el atlas nacional; se anota que no sirve para cartografía local.
- Dónde se reutiliza: `config/sources.yaml` (mgn-*), ADR-005 (atlas).

## S-008 · 2026-09-06 · Los metadatos de Socrata tipan las columnas
- Contexto: B-025.
- Qué funcionó: `api/views/<id>.json` declara `number`, `text` y `calendar_date` por columna; con `code_cols` para conservar los códigos como texto, un mismo descargador sirve para las cinco tablas SODA sin expresiones regulares por fuente. MinTIC declara todo como `text` y es la única que necesita `numeric_cols`.
- Dónde se reutiliza: `src/iif/acquire/soda.py::typing_from_metadata`; `config/sources.yaml`.

## S-009 · 2026-09-06 · En `ptgf`, `renglon` es el código municipal DIVIPOLA
- Contexto: ADR-007 preveía un crosswalk por nombre normalizado con overrides.
- Qué funcionó: `dpto_ccdgo || lpad(renglon, 3)` reproduce el DIVIPOLA de 5 dígitos para los 1.115 municipios con fila en `ptgf` (cobertura 100 % en los 14 trimestres contra MGN 2024 y población DANE); `renglon = 999` es el total departamental. El nombre solo se usa como comprobación (92 % coincide tras normalizar; el resto son alias como "SANTAFE DE BOGOTA D." o "CARMEN DE VIBORAL").
- Dónde se reutiliza: `dbt/models/staging/sfc/stg_sfc__ptgf.sql`; adenda de ADR-007. Pendiente comprobar lo mismo en `kx2f`.

## S-010 · 2026-09-06 · `kx2f` sigue la misma convención: `renglon` es el DIVIPOLA municipal
- Contexto: S-009 se comprobó en `ptgf`; el plan suponía que `kx2f` venía sin DIVIPOLA.
- Qué funcionó: en `kx2f`, `dpto_ccdgo || lpad(renglon, 3)` cubre el 100 % de las filas geográficas en los 20 cortes (2021Q1 a 2025Q4); 64 nombres difieren del DANE solo por grafía. El crosswalk por nombre de ADR-007 queda como prueba de consistencia en ambas tablas.
- Dónde se reutiliza: `stg_sfc__kx2f`, `int_sfc_geo_long`, `iif crosswalk geo-report --fuente kx2f`.

## S-011 · 2026-09-06 · Ninguna serie de la SFC es acumulada en el año
- Contexto: antes de fijar la regla de anualización de las 98 variables (sumar flujos, tomar el cuarto trimestre en stocks) había que descartar que las transacciones vinieran acumuladas desde enero, error que multiplicaría por cuatro cualquier agregado anual.
- Qué funcionó: la firma de una serie acumulada es que el primer trimestre cae a un cuarto del cuarto trimestre anterior y que dentro del año crece de forma monótona. Se midió en las 164 series de las dos tablas: la mediana de Q1 sobre el Q4 anterior está entre 0,73 y 1,54, nunca cerca de 0,25, y ninguna serie cumple las dos condiciones.
- Dónde se reutiliza: `dbt/seeds/dim_variable.csv` (`regla_anualizacion`); la prueba se repetirá cuando la SFC publique columnas nuevas.

## S-012 · 2026-09-06 · El panel nuevo sí varía dentro del panel
- Contexto: el defecto que originó el proyecto fue un panel trimestral cuya dependiente solo cambiaba una vez al año (64,3 % de log-diferencias exactamente cero).
- Qué funcionó: construir la dependiente a frecuencia anual verdadera sobre el PIB real per cápita del DANE. El panel departamental 2018-2025 tiene 231 observaciones de crecimiento, **ninguna** exactamente cero, siete valores distintos por departamento y el perfil esperado de la pandemia (mediana de −9,3 % en 2020 y +8,4 % en 2021). Una prueba dbt (`assert_panel_departamento_varia_dentro_del_anio`) falla si los ceros exactos superan el 5 %.
- Dónde se reutiliza: `mart_panel_departamento_anual`, `mart_panel_municipio_anual`; R-05.

## S-013 · 2026-09-06 · Las variables crudas de la SFC miden población
- Contexto: antes de construir el índice había que decidir la normalización.
- Qué funcionó: medir la correlación de cada candidata con la población departamental. Va de 0,58 a 0,94 (pagos 0,94; cuentas de ahorro 0,92). Un índice sobre variables sin normalizar tendría como primer factor el tamaño del departamento. Con conteos por 10.000 habitantes y montos como porcentaje del producto, la correlación cae a un rango de −0,28 a 0,69, que ya es relación económica y no aritmética.
- Dónde se reutiliza: `config/index.yaml` (normalización), ADR-015, `tests/test_index.py::test_normalizacion_elimina_la_escala_de_la_unidad`, que reproduce el problema en un panel sintético antes de comprobar que la normalización lo quita.

## S-014 · 2026-09-06 · Medir el mapa contra el área real de Colombia
- Contexto: B-039. Un mapa mal proyectado puede verse "casi bien" y pasar la revisión a ojo.
- Qué funcionó: comprobar que la suma de las áreas esféricas de los 33 departamentos coincide con el área conocida de Colombia (1.142.000 km² sobre una esfera de 510 millones: 0,0281 estereorradianes). El exportador daba 590 antes del arreglo y 0,02817 después. Es una prueba de una línea que detecta el fallo de giro, los anillos degenerados y una proyección equivocada, sin mirar el mapa.
- Dónde se reutiliza: la comprobación entra como prueba del exportador del atlas.

## S-015 · 2026-09-06 · El atlas no depende de ningún CDN
- Contexto: al abrir la página en un navegador sin salida a internet, los cuatro filtros y el mapa se caían: Quarto carga Observable Inputs desde jsDelivr y las celdas quedaban esperando ese módulo.
- Qué funcionó: vendorizar d3 y topojson-client en `atlas/lib/` y construir los filtros con HTML plano. La página entera se dibuja sin una sola petición externa, que es lo que corresponde a un artefacto de investigación pensado para durar; además la guía de visualización pide justamente que los filtros sean interfaz corriente y no componentes del gráfico.
- Dónde se reutiliza: `atlas/index.qmd` (helper `control`), `atlas/lib/`.


## B-040 · 2026-09-06 · Ninguna capital se rotulaba: un booleano que viajó como texto
- Contexto: el mapa municipal rotula solo las capitales departamentales; el exportador manda `es_capital` en `series_municipio.json`.
- Qué pasó: la capa de nombres no dibujaba nada y el mapa no daba ningún aviso.
- Causa raíz: `build_series` pasaba **todos** los acompañantes por `str()`, regla pensada para los códigos DIVIPOLA, que llevan ceros a la izquierda y un número los perdería. Con un booleano, `str(True)` produce `"True"`, y en el navegador `"True"` no es ni `true` ni `"true"`: la comparación era falsa en las 1.123 filas.
- Regla: un fallo de tipo que solo se manifiesta como "no se dibuja" hay que convertirlo en un fallo de prueba. Los datos publicados declaran su tipo y una prueba lo comprueba.
- Evidencia: `src/iif/export/atlas.py::_escalar`; `tests/test_atlas.py::test_los_acompanantes_conservan_su_tipo`.

## B-041 · 2026-09-06 · Girar sobre un encuadre ya ajustado saca el mapa del marco
- Contexto: las vistas en volumen inclinan el país con una matriz sobre el grupo de SVG, en vez de reproyectar 1.121 geometrías en cada cambio.
- Qué pasó: la vista municipal salía cortada por los dos lados.
- Causa raíz: la proyección se ajustaba al lienzo (660 × 646) y **después** se giraba 28°. Un rectángulo de 544 × 646 girado mide 783 de ancho: 123 puntos fuera del marco por lado.
- Cómo se encontró: midiendo en el navegador la caja del grupo del mapa contra la caja del SVG, no mirando la captura.
- Regla: la escala de ajuste se calcula sobre las esquinas **ya transformadas**. Toda vista que gire o aplaste calcula su encuadre después de la transformación, nunca antes.
- Segundo hallazgo del mismo sitio: el archipiélago de San Andrés está a 700 km del continente y se llevaba una quinta parte del ancho del lienzo para dibujar un punto. Sale del encuadre y va como ficha rotulada fuera de escala, viva para el ratón como cualquier departamento; un inserto proporcional no servía porque lo que ocupa el recuadro es el mar entre las dos islas.
- Evidencia: `atlas/index.qmd`, celda `vistaGeo` (`ES_INSULAR`, `anchoUtil`, `subir`).

## B-042 · 2026-09-06 · La limpieza de oyentes colgaba de un evento que el navegador ya no dispara
- Contexto: los tres paneles del atlas se suscriben al bus de foco y tienen que darse de baja cuando OJS los reemplaza.
- Qué pasó: la baja nunca ocurría. Cada cambio de año, indicador o vista dejaba tres oyentes más apuntando a nodos ya desechados.
- Causa raíz: la baja se registraba con `DOMNodeRemovedFromDocument`, un evento de mutación **retirado de Chromium**. No falla: simplemente no se dispara nunca.
- Regla: en OJS la baja se hace con `invalidation`, que es el mecanismo del propio entorno. Una suscripción sin baja comprobada es una fuga; se comprueba contando, no leyendo.
- Evidencia: `atlas/index.qmd` (`invalidation.then(quitar)` en los tres paneles); comprobado en el navegador con ocho cambios de año seguidos.

## B-043 · 2026-09-06 · El atenuado en la cara dejaba los cantos a plena tinta
- Contexto: al filtrar por región o departamento, las unidades de fuera se atenúan para dar contexto sin competir.
- Qué pasó: al bajar a los municipios de Antioquia, el resto del país aparecía como una masa gris oscura, más llamativa que la selección.
- Causa raíz: la opacidad estaba puesta en la cara del bloque y no en el grupo, así que las 26 copias del canto seguían pintándose enteras. El mismo error de encuadre agravaba el efecto: el mapa no se acercaba al filtro y los 118 municipios elegidos eran una mancha del tamaño de una uña.
- Regla: una propiedad que describe a la unidad (atenuar, ocultar, resaltar) va en el grupo de la unidad, nunca en una de sus piezas.
- Evidencia: `atlas/index.qmd` (`opacidadDe` sobre `g.unidad`; `enFoco` en `vistaGeo`).

## B-044 · 2026-09-06 · `table-layout: fixed` lee la primera fila, y los anchos estaban en el cuerpo
- Contexto: el ranking del atlas con nombres municipales largos.
- Qué pasó: al fijar el reparto de la tabla para que los nombres no empujaran las cifras, el encabezado se solapó ("DEPARTAMENTO" encima de "VALOR").
- Causa raíz: con `table-layout: fixed` mandan los anchos de la **primera** fila; los anchos estaban en las celdas del cuerpo, así que el encabezado se repartió a partes iguales.
- Regla: con reparto fijo, los anchos van en un `<colgroup>`, que es el único sitio que no depende de qué fila se dibuje primero.
- Evidencia: `atlas/index.qmd`, `panelContexto`.

## S-016 · 2026-09-06 · Medir la página en el navegador, no mirarla
- Contexto: B-041, B-042 y B-043 son defectos que una captura enseña a medias o no enseña: un recorte de 60 puntos parece encuadre, una fuga de oyentes no se ve, y un gris de más parece una decisión de diseño.
- Qué funcionó: un guion de Playwright que, además de las capturas, imprime números por vista: cuántas unidades y cuántos nodos hay, la caja del mapa contra la caja del lienzo (desbordes por los cuatro lados), el tiempo de ocho cambios de año seguidos y cuántos mapas quedan vivos en el documento. Los tres defectos aparecieron como números malos antes que como imágenes feas.
- Dónde se reutiliza: el mismo guion vale para cualquier página del sitio con gráficos; la comprobación de desbordes es la que hay que repetir cuando cambie el encuadre.

## B-045 · 2026-09-06 · El sitio dependía de un ajuste que solo existe en una consola
- Contexto: el sitio se publica en Vercel desde la rama `site`, que CI reescribe en cada push a `main`. Para que ese despliegue fuera el de producción hacía falta que en la consola de Vercel la Production Branch fuera `site`.
- Qué pasó: `https://financial-inclusion-colombia.vercel.app/` respondió 404 durante horas, con CI en verde todo el tiempo y el autor intentando el ajuste dos veces.
- Causa raíz: dos cosas, y la segunda es la de fondo. La inmediata: cambiar la rama de producción **no promueve los despliegues que ya existen**, solo afecta a los siguientes, y `main` está ignorada a propósito, así que el dominio de producción nunca tuvo nada asignado. La de fondo: el mecanismo de publicación vivía en un ajuste invisible desde el repositorio, que nadie puede leer en una revisión, que no aparece en ningún diff y que ni el autor ni el agente podían verificar (el conector de Vercel devuelve 403 y 404 sobre este proyecto).
- Cómo se encontró: midiendo tres cosas en vez de mirar la consola. El dominio de producción daba 404 con `DEPLOYMENT_NOT_FOUND`, que significa "este dominio no apunta a nada" y no "el build falló". La URL de la rama (`...-git-site-...`) daba 302 al SSO, y esa URL **solo existe si la rama tiene despliegues**: luego Vercel sí construía `site` y los archivaba como vista previa. Y hubo un despliegue nuevo de `site` a las 23:08 con producción todavía en 404, lo que descartaba que fuera cuestión de esperar.
- Regla: un despliegue se declara en el repositorio y se verifica contra el dominio público. CI despliega producción con la CLI de Vercel, que no está atada a ninguna rama, y después comprueba que el dominio devuelve 200; si no, el build falla. Un build verde con el sitio inalcanzable es peor que un build rojo, porque nadie lo mira.
- Evidencia: `.github/workflows/ci.yml`, pasos «Desplegar produccion en Vercel» y «Comprobar el dominio de produccion»; adenda 4 de ADR-005.

## B-046 · 2026-09-06 · El atlas publicado no encontraba sus datos
- Contexto: `atlas/index.qmd` carga la geometría y las series con `FileAttachment("data/*.json")`.
- Qué pasó: en el sitio desplegado, las seis celdas del atlas mostraban `OJS Runtime Error: Unable to load file`. En local no se veía porque después de cada exportación yo copiaba los JSON a `_site` a mano, sin darme cuenta de que ese `cp` era lo único que los ponía allí.
- Causa raíz: Quarto copia a `_site` los recursos que ve **enlazados en el HTML**; las rutas de `FileAttachment` viven dentro de una celda de OJS y no las descubre. La portada declaraba `resources: lib/*.js` y no `data/*.json`, así que los datos nunca se publicaban.
- Regla: todo recurso que solo se nombre dentro de una celda de OJS se declara en `resources`. Y la comprobación de que una página funciona se hace sobre el sitio construido sin tocarlo a mano: un `cp` de conveniencia durante la revisión esconde exactamente este fallo.
- Evidencia: `atlas/index.qmd`, bloque `resources`.

## B-047 · 2026-09-07 · Una exposición inicial medida en una variable que no existe en el año base
- Contexto: el shift-share se contrasta con exposiciones de placebo (ingreso y urbanización iniciales) medidas en 2018.
- Qué pasó: la batería completa moría con `exog does not have full column rank`, un error que nombra al estimador y no a la causa.
- Causa raíz: la exposición de ingreso se tomó de `log_pib_rezago`, que en 2018 es toda vacía porque el rezago necesita 2017. La columna llegaba al estimador llena de nulos, se convertía en un vector de ceros al cruzarla con la adopción nacional, y el error saltaba tres funciones más abajo.
- Regla: una exposición inicial comprueba su cobertura en el año base antes de usarse, y falla nombrando la variable y el año. El error debe saltar donde está la causa, no donde se manifiesta.
- Evidencia: `src/iif/econ/designs.py::exposicion_inicial`.

## S-017 · 2026-09-07 · La econometría se probó donde la verdad se conoce
- Contexto: un resultado nulo sobre datos reales no distingue entre "no hay efecto" y "el código no lo vería aunque lo hubiera".
- Qué funcionó: doce pruebas sobre paneles sintéticos con estructura sabida —efecto real, tendencia común disfrazada de efecto, factor con cargas heterogéneas, patrón espacial, caminata aleatoria— antes de mirar un solo coeficiente real. Destaparon dos cosas que la tabla final no habría enseñado: el desmediado de dos vías en un panel desbalanceado necesita proyecciones alternadas (sin ellas el bootstrap comparaba un coeficiente distinto del estimador), y la prueba CD de Pesaran tiene poca potencia con cargas de media cero, que es una propiedad de la prueba y hay que saberla para leerla.
- Dónde se reutiliza: `tests/test_econ.py`; el tamaño del bootstrap se mide sobre veinte paneles, no sobre uno, porque uno solo rechaza al 5 % una de cada veinte veces por definición.


## S-018 · 2026-09-07 · El problema de despliegue se resolvió quitando la superficie
- Contexto: publicar el sitio Quarto costó cinco intentos —rama de producción que no promueve despliegues existentes (B-045), recursos del atlas no declarados (B-046), un token con el ámbito equivocado— y cada arreglo dejaba una pieza más de andamiaje: `vercel.json`, `.github/site/vercel.json`, la rama `site`, un secreto de repositorio y un paso de CI que comprobaba un dominio.
- Qué funcionó: preguntar si ese sitio tenía que existir. No tenía: la investigación entera ya vive en la página del portafolio, atlas incluido, y dos superficies para el mismo contenido garantizan que una se quede sin dueño. Al retirarlo desaparecen de golpe el ajuste invisible de consola, el token y los cinco pasos de publicación, sin perder nada que alguien estuviera leyendo.
- Regla derivada: antes de invertir en publicar algo, comprobar que ese algo tiene que existir. Un despliegue que cuesta cinco intentos casi siempre está resolviendo el problema equivocado.
- Dónde se reutiliza: ADR-005, adenda 5. `quarto render` se queda dentro de `make check`, que es lo que de verdad daba valor: la prueba de que la documentación compila.

## B-048 · 2026-09-16 · El repositorio anunciaba su página pública en el host anterior del portafolio
- Contexto: el portafolio se mudó de `proyecto-davirson-git.vercel.app` a `davirson.com` en septiembre de 2026, y la página pública de esta investigación vive allí (ADR-005, adenda 5).
- Qué pasó: los dos README, la guía del proyecto y `CITATION.cff` seguían publicando la dirección anterior. El enlace no estaba roto —el host viejo redirige a propósito y devuelve 200—, así que ninguna comprobación lo vio; lo que estaba mal era la dirección que el repositorio declara como suya. `CITATION.cff` era el caso peor: apuntaba a `financial-inclusion-colombia.vercel.app`, el proyecto de Vercel que la adenda 5 manda borrar, así que la URL de cita se rompe en cuanto se haga esa limpieza.
- Causa raíz: la dirección pública está copiada en cinco sitios y ninguno tiene dueño único. El portafolio resolvió lo mismo con una constante (`lib/config/site.ts`); aquí son texto en Markdown y un cambio de dominio no los alcanza.
- Regla: la dirección pública del proyecto vive en los dos README, en la guía y en `CITATION.cff`, y los cuatro se revisan juntos cuando el portafolio cambie de host. Un enlace que redirige no es un enlace correcto → esta entrada y R-12.
- Evidencia: `grep -rn "proyecto-davirson-git" .` solo debe devolver `docs/decisiones/` y este archivo, que son registros fechados y no se reescriben.
- Estado: cerrada en los README, la guía y `CITATION.cff`; abierta en `_quarto.yml` (`site-url`), que sigue apuntando al sitio Quarto retirado y no se toca sin poder correr `quarto render`.

## B-049 · 2026-09-23 · Una propiedad medida en una ventana, afirmada para todas
- Contexto: ADR-019 y ADR-021 justifican la reconciliación jerárquica con que la suma de los 33 departamentos cuadra con el total nacional del DANE.
- Qué pasó: ambos afirmaban "menos del 0,08 % **en todos los años**, máximo 0,072 % en 2025". Es falso. Esa comprobación se corrió solo sobre 2018–2025, que es la ventana del backtest. Sobre 2005–2025 la brecha máxima es **1,284 % en 2009**, y los años 2005–2012 van de 0,23 % a 1,28 %.
- Causa raíz: la comprobación exploratoria se hizo sobre el subconjunto que interesaba para el backtest, y su resultado se generalizó a la serie completa al redactar el ADR sin volver a medir. El dato correcto siempre estuvo disponible.
- Regla: R-09 (toda cifra publicada traza a una prueba) → la traza tiene que incluir **sobre qué muestra** se midió, no solo el número. Una cifra sin su ventana no es trazable.
- Evidencia: `data/interim/dane/pib_departamento_anual.parquet`; la no aditividad de 2005–2012 viene de la retropolación del DANE a base 2015, que no impone suma exacta en los años reconstruidos.
- Consecuencia útil: corregido, el ADR queda mejor. La restricción de agregación es exacta en la ventana donde se reconcilia (2018–2025, ≤ 0,072 %) y aproximada en el tramo antiguo del entrenamiento, y eso ahora está escrito.
- Estado: cerrada

## B-050 · 2026-09-23 · Rutas locales en un documento del repositorio
- Contexto: `docs/HOJA_DE_RUTA_PROYECCION.md`, rescatado de un directorio temporal.
- Qué pasó: el documento traía tres rutas del equipo donde se redactó, incluida una ruta local en un bloque de comandos, y referencias a un directorio de trabajo externo al repositorio.
- Causa raíz: el texto se escribió como nota de sesión, no como documento del repositorio, y al versionarlo no se revisó contra las reglas del proyecto.
- Regla: R-04 (nunca rutas absolutas) y R-08 (nunca rutas locales) → revisar todo texto importado desde fuera antes de versionarlo, no solo el que se escribe aquí.
- Evidencia: `grep -rnE "~/Desktop|C:\\Users|/c/Users" docs/` ahora no devuelve nada.
- Estado: cerrada

## B-051 · 2026-09-23 · El manifiesto guardaba rutas con el separador del sistema
- Contexto: `acquire/{dane,mgn,soda}.py` escriben `path` en `data/raw/manifest.jsonl`, que se versiona y se verifica en Linux.
- Qué pasó: la ruta se serializaba con `str(path.relative_to(REPO_ROOT))`; una descarga hecha en Windows habría escrito `data\raw\...`, que `iif manifest verify` y `fetch_data.py` no resuelven en Linux.
- Causa raíz: `str(Path)` depende del sistema y la serialización estaba copiada en tres módulos.
- Regla: R-04 y R-07. Toda ruta persistida pasa por `manifest.rel_path` (POSIX) y se lee con `manifest.resolve_path`.
- Evidencia: `tests/test_acquire.py::test_manifest_paths_use_forward_slashes`, `::test_manifest_verify_accepts_backslash_records`.
- Estado: cerrada

## B-052 · 2026-09-23 · Un año de partición numérico con nulos rompía la descarga SODA
- Qué pasó: `astype(int)` sobre la columna de partición fallaba con `IntCastingNaNError` antes del `fillna` que debía mandar el nulo a `anio=sin_fecha`.
- Causa raíz: la conversión de tipo iba antes del tratamiento del faltante, y solo la rama de fechas tenía prueba.
- Regla: R-13. El faltante se trata antes de cualquier conversión, y cada rama de tipado lleva su prueba.
- Evidencia: `tests/test_acquire.py::test_soda_numeric_year_partition_with_nulls`.
- Estado: cerrada

## B-053 · 2026-09-23 · Python y dbt no leían el mismo warehouse
- Qué pasó: dbt, el Makefile y CI siguen `IIF_DUCKDB_PATH` (en CI, `/tmp/iif.duckdb`), pero `export/atlas.py`, `econ/frame.py`, `index/run.py` y `metodologia/indice.qmd` tenían fijo `db/iif.duckdb`.
- Causa raíz: la ruta del warehouse era un literal copiado en cuatro sitios, no una constante de `iif.config`.
- Regla: R-04 y R-15. La ruta vive solo en `config.DUCKDB_PATH`.
- Evidencia: `tests/test_cli.py::test_duckdb_path_follows_the_same_variable_as_dbt`; `grep -rn '"iif.duckdb"' src metodologia` solo devuelve `config.py`.
- Estado: cerrada

## B-054 · 2026-09-23 · `iif forecast` imprimía "2713" en lugar de la marca de éxito
- Causa raíz: escape Unicode escrito sin la barra, en un camino sin prueba.
- Regla: la marca de éxito se escribe literal, como en los demás comandos.
- Evidencia: `src/iif/cli.py`, comando `forecast`.
- Estado: cerrada

## B-055 · 2026-09-23 · Una prueba de semilla comparaba el DIVIPOLA con la numeración interna de la SFC
- Qué pasó: la prueba de `xw_sfc_municipio_overrides` exigía `left(mpio_ccdgo,2) = lpad(unicap,2,'0')`; `unicap` 1 es Antioquia ('05'). Pasaba solo porque la semilla está vacía.
- Causa raíz: se confundió `unicap` con DIVIPOLA, y una prueba sobre una tabla vacía nunca se ejerció.
- Regla: el prefijo departamental se prueba contra `xw_sfc_departamento`. Una prueba sobre una semilla vacía no es evidencia.
- Evidencia: `dbt/tests/assert_overrides_municipio_en_su_departamento.sql`.
- Estado: cerrada

## B-056 · 2026-09-23 · Los scripts de Snowflake citaban un diseño que no se construyó
- Qué pasó: `snowflake/04_dynamic_table_example.sql` usaba `pull_id`, `is_current` y una regla `mean` inexistentes, y descartaba stocks de años incompletos; `03_clone_vintage.sql` citaba `FCT_PIB_DEPARTAMENTO_ANUAL` y `pib_cop_millones`.
- Causa raíz: se escribieron contra ADR-002 y no contra los modelos dbt, y nunca se ejecutaron.
- Regla: un script fuera de dbt que replica su lógica cita el modelo de origen y se revisa cuando ese modelo cambia.
- Evidencia: `snowflake/03_clone_vintage.sql`, `snowflake/04_dynamic_table_example.sql`.
- Estado: cerrada en el texto; sin ejecutar

## B-057 · 2026-09-23 · Una regla dura que solo vivía en una prueba
- Qué pasó: `build_index` aceptaba PCA con KMO < 0,5 y pesos implícitos negativos, incluidos los congelados en `config/index.yaml`. R-17 solo se comprobaba sobre un panel sintético.
- Causa raíz: la regla se probó fuera de la ruta de publicación.
- Regla: una regla dura se hace cumplir donde se publica, y la prueba comprueba que esa ruta falla.
- Evidencia: `src/iif/index/build.py` (`KMO_MINIMO`, comprobación de signo); `tests/test_index.py::test_pesos_congelados_con_carga_negativa_no_se_publican`. El índice actual no cambia (diferencia máxima 8,9e-16).
- Estado: cerrada

## B-058 · 2026-09-23 · "Los mismos modelos en BigQuery" sin haberlos compilado
- Qué pasó: 20 modelos usaban `cast(... as varchar|double)`, las semillas declaraban `varchar(2)` y el panel legado usaba `read_parquet_path`; nada de eso existe en BigQuery.
- Causa raíz: el SQL se validó solo en DuckDB y la portabilidad se afirmó sin compilar contra el otro dialecto.
- Regla: tipos y funciones de dialecto van por macro (`dbt/macros/portable_types.sql`); un modelo solo DuckDB se declara con `enabled`.
- Evidencia: `dbt/macros/portable_types.sql`, `dbt/dbt_project.yml`; `dbt build` en DuckDB 377/377.
- Estado: abierta hasta la primera compilación real en BigQuery

## B-059 · 2026-09-23 · La capa de proyección degradaba en silencio
- Qué pasó: `reparto_proporcional` devolvía la base sin anclar con etiqueta de reconciliada; un NaN en un departamento contagiaba a los 33; un horizonte no contiguo o un total nacional desfasado encadenaban años distintos; `pivot_table` promediaba duplicados; un nombre de modelo mal escrito se volvía NaN.
- Causa raíz: se priorizó que el módulo no lanzara errores sobre que fallara donde está la causa (misma lección que B-047).
- Regla: un paso publicable falla con nombre y año; nunca devuelve su entrada con otra etiqueta. Consecuencia: cuando el DANE publique 2026, el `HORIZONTE` fijo 2026–2028 hará fallar la corrida en vez de etiquetar mal.
- Evidencia: `forecast/reconcile.py`, `forecast/run.py::_exigir_*`, `forecast/frame.py`, `forecast/models.py`; `tests/test_forecast.py`.
- Estado: cerrada

## B-060 · 2026-09-23 · `rolling_origin(h)` medía siempre el primer paso
- Causa raíz: el parámetro se añadió sin usarse en el índice del pronóstico medido. Con h = 1, que es lo publicado, nada cambia.
- Regla: todo parámetro público tiene una prueba que lo ejerce con un valor distinto del de por defecto.
- Evidencia: `tests/test_forecast.py::test_rolling_origin_a_h_pasos_mide_el_anio_objetivo`.
- Estado: cerrada

## B-061 · 2026-09-23 · La clave de BigQuery se escribía a través de un shell que le quitaba las comillas
- Qué pasó: interpolar el secreto con `${{ }}` dentro del `run:` inserta el JSON en el texto del script antes de que bash lo lea; sus comillas rompen el entrecomillado y el archivo sale corrupto. Además es una vía de inyección.
- Causa raíz: un secreto interpolado en el script en vez de pasado como dato.
- Regla: un secreto o cualquier `github.*` entra a un `run:` solo por `env:`.
- Evidencia: `.github/workflows/ci.yml`, paso de la clave de servicio.
- Estado: cerrada

## B-062 · 2026-09-23 · CI y `make check` eran dos copias de los mismos pasos
- Qué pasó: CI repetía los comandos a mano y ya había derivado (no validaba el YAML de los workflows); conservaba `contents: write` después de retirar el sitio (S-018).
- Causa raíz: dos listas de los mismos comandos sin un dueño.
- Regla: CI llama a objetivos de `make`; un comando vive solo en el Makefile. Los permisos se revisan cuando se retira un paso de publicación.
- Evidencia: `.github/workflows/ci.yml`, `Makefile`.
- Estado: cerrada; la primera corrida de CI es la prueba

## B-063 · 2026-09-23 · El Makefile y `requirements.txt` suponían un entorno que no es el del autor
- Qué pasó: `QUARTO_PYTHON` apuntaba a `.venv/bin/python` (en Windows es `.venv/Scripts/python.exe`), `make data` llamaba a `python3` saltándose uv (R-02), `make lint` leía YAML sin `encoding`, `.PHONY` listaba un `atlas` inexistente, y `requirements.txt` no tenía `dbt-bigquery` ni sus dependencias.
- Causa raíz: el Makefile solo se había corrido en Linux, y nada regenera `requirements.txt` cuando cambia `uv.lock`.
- Regla: rutas del venv según el sistema; Python siempre por `uv run`; archivos de texto con `encoding='utf-8'`; tras cada `uv lock`, `uv export --frozen --no-hashes --no-dev --no-emit-project -o requirements.txt`.
- Evidencia: `Makefile`, `requirements.txt`, `.gitattributes` (LF forzado en `*.sh` y `Makefile`).
- Estado: cerrada

## B-064 · 2026-09-23 · Sarma rellena faltantes con cero
- Qué pasó: `index/build.py::_sarma` hace `fillna(0.0)`; cuatro filas reales (Guainía 2019; Vaupés 2018, 2019 y 2025) entran a la sensibilidad "índice alternativo: Sarma" con N = 231 cuando la base usa 228. Con R-13 aplicado el coeficiente pasa de −0,105 (p 0,336) a −0,108 (p 0,326). Además el máximo se toma sobre todos los años, no sobre la ventana congelada.
- Causa raíz: la fórmula de distancia se implementó sin mirar la regla de faltantes.
- Regla: R-13. Cambia una cifra publicada, así que va primero a un ADR (R-11).
- Estado: cerrada con ADR-025 (B-085)

## B-065 · 2026-09-23 · Diebold-Mariano agrupado trata 264 pares como independientes
- Qué pasó: los 33 departamentos de un mismo origen comparten el choque. La prueba agrupada da p = 2e-7; con la diferencia media de pérdidas por origen (8 orígenes), p = 0,29. La ventaja de la combinación sobre el ingenuo en ADR-020 descansa sobre todo en 2021 (−14,9 pp). Aparte, `evaluar` aprueba con ganancia > 0 y cobertura ≥ 90 % sin usar el valor p que exige ADR-020.
- Causa raíz: la inferencia sobre errores de pronóstico no se agrupó en el nivel donde está la dependencia.
- Regla: en un panel, la prueba sobre errores de pronóstico se agrupa por año de origen o usa HAC sobre la media transversal. Requiere ADR.
- Estado: cerrada con ADR-023 (medición reproducida: correlación intraorigen 0,60, 3 de 8 orígenes ganados, +8,3 % sin 2021, efecto detectable de 6,1 pp con 8 orígenes). `diebold_mariano` agrupa por origen; la puerta exige ganancia también sin el mejor origen; `resultados.json` y el atlas publican la lectura completa. Evidencia: `tests/test_forecast.py::test_diebold_mariano_agrupa_por_origen_y_no_confunde_un_choque_comun_con_ventaja`, `::test_la_puerta_frena_una_ganancia_que_es_un_solo_anio` y la prueba lenta sobre el panel real, que fija las cifras de ADR-023

## B-066 · 2026-09-23 · La documentación contaba cifras y un estado que ya no eran
- Qué pasó: los README atribuían KMO 0,314 a acceso y 0,404 a uso (son uso y profundidad; acceso tiene una sola variable); decían "anclada al consenso" cuando el ancla es el WEO del FMI; el abstract en español negaba resultados; `index.qmd` daba las fases 2 y 3 por pendientes; `modelo-de-datos.qmd` describía `dim_vintage` y hechos que no existen; la hoja de ruta repetía la brecha de 0,07 % sin su ventana (B-049).
- Causa raíz: las cifras se copian a mano y ningún commit de código revisa las páginas de estado; un arreglo de cifra se hizo solo en el archivo donde se detectó.
- Regla: R-09 y R-16. Un arreglo de cifra se busca con grep en todo el repositorio; al cerrar sesión se revisan el estado del README, `index.qmd` y la guía.
- Evidencia: `data/processed/indice_diagnosticos.csv`, `data/processed/forecast/resultados.json`.
- Estado: cerrada en el texto; abierta la prueba que compare README y JSON/CSV

## S-019 · 2026-09-23 · Las cifras publicadas viven en una sola prueba con su muestra
- Contexto: B-049 enseñó que una cifra sin ventana no es trazable.
- Qué funcionó: `dbt/tests/assert_cifras_publicadas.sql` fija 264/231 filas y crecimientos departamentales, 7.861/1.123 municipales, 1.121 polígonos MGN, 96 y 98 variables (70 + 8 + 20), 19/17 canales, 603.232 filas de ptgf y las medianas de 2020 y 2021, cada una con dónde se publica y sobre qué muestra se mide.
- Dónde se reutiliza: toda cifra nueva del README o de la guía entra a esta prueba o a una prueba pytest antes de publicarse.

## B-067 · 2026-09-23 · Las series del atlas en `main` salieron de un warehouse de otra rama
- Contexto: al regenerar el atlas para ADR-023, las series observadas (variables en % del PIB y los subíndices del IIF) cambiaron aunque ni los datos ni el código de `main` las tocan.
- Qué pasó: el commit 6b9e7dc exportó el atlas desde un DuckDB construido con la rama `auditoria-potencia-y-denominador` (f7903b5, denominador rezagado de ADR-017), que no está fusionada. Desde `main`, `iif atlas` reproduce exactamente las series del 6 de septiembre, no las publicadas. El atlas versionado no traza al código que lo acompaña (R-09).
- Causa raíz: el warehouse local es estado compartido entre ramas; `iif atlas` lee lo último que se construyó, no lo que el código de la rama construiría.
- Regla: antes de exportar el atlas o cualquier salida versionada, `dbt build` desde la rama que se va a commitear. Un JSON exportado lleva la rama de la que salió.
- Decisión provisional: el PR de ADR-023 solo reemplaza el bloque `proyeccion.backtest` y no toca las series, para no mover cifras publicadas sin decisión del autor. Se resuelve al fusionar `auditoria-potencia-y-denominador` y regenerar el atlas desde `main`.
- Aviso: esa rama usa también los números B-051 a B-055 para otras entradas y ya arregla `IIF_DUCKDB_PATH`; al fusionarla hay que renumerar sus entradas y resolver el solape con B-053.
- Estado: cerrada al fusionar la rama (2026-09-23). Tras `dbt build`, `iif index`, `iif econ`, `iif curva` e `iif atlas` desde el código fusionado, las series observadas del atlas coinciden con las publicadas y `econ/resultados.json` coincide cifra a cifra con el de la rama; el atlas ya traza a su código

## Nota de fusión · 2026-09-23 · Entradas de la rama `auditoria-potencia-y-denominador`
Las diez entradas que siguen se escribieron el 2026-09-11 en esa rama con los números B-048 a B-056 y S-019, que `main` usó después para otras entradas. Al fusionar se renumeraron a B-068 a B-076 y S-020, en la bitácora y en todas las líneas que la rama aportó al código, las pruebas y la documentación. Conservan su fecha original. B-075 (la base se construía en un sitio y se leía en otro) y B-053 describen el mismo error, encontrado dos veces por separado.

## B-068 · 2026-09-11 · La I de Moran se calculó sobre el crecimiento crudo y no sobre los residuos
- Contexto: ADR-016 punto 3 pide dependencia espacial medida, no supuesta, y el README publica una tabla de I de Moran por año con su inferencia por permutación.
- Qué pasó: la tabla publicada marca 2022 (0,22; p = 0,039) y 2025 (0,23; p = 0,047) como los años con dependencia espacial, y el README afirma a continuación que el SLX la absorbe. Calculada sobre los residuos del modelo base, la dependencia no está en 2022 ni en 2025 sino en 2019 (I = 0,243; p = 0,025), y sobre los residuos del SLX sigue ahí prácticamente intacta (I = 0,242; p = 0,039).
- Causa raíz: `run.py` pasaba a `moran_i` la serie `crecimiento` de la muestra, que es la variable dependiente cruda. Un Moran sobre la dependiente cruda mide si los vecinos crecen parecido —que es un hecho conocido sobre Colombia y no una propiedad del modelo—; lo que la batería necesita saber es si al modelo le queda dependencia espacial sin explicar, y eso solo lo dicen los residuos. La función `moran_i` estaba bien; el objeto que se le daba, no.
- Regla: R-09. Una frase publicada sobre lo que un estimador absorbe se acompaña del contraste que lo demuestra, sobre los residuos de ese estimador. Si no existe el contraste, no se escribe la frase.
- Evidencia: `src/iif/econ/run.py::run`, `tests/test_econ.py::test_moran_se_mide_sobre_residuos_y_no_sobre_la_dependiente`.
- Estado: cerrada

## B-069 · 2026-09-11 · El texto publicado prometía un rezago del índice que el código nunca construyó
- Contexto: el README declara, en su sección de pregunta de investigación, que un rezago del índice ordena la relación en el tiempo y que no constituye una estrategia de identificación causal.
- Qué pasó: no existe ningún rezago del índice en `src/iif/econ/`. Las únicas apariciones de la palabra son el rezago espacial del SLX y el rezago del ingreso, que es el término de convergencia. El regresor de `run.py` es `iif_compuesto`, el índice contemporáneo del mismo año cuyo crecimiento se explica.
- Causa raíz: la frase se escribió describiendo la intención del diseño y nunca se contrastó contra la constante `X` de `run.py`. Nada en la cadena de pruebas comparaba el texto con la especificación, porque las pruebas miran cifras y esta era una afirmación en prosa.
- Regla: R-09, extendida: una afirmación sobre la especificación es una cifra publicada más. La especificación se escribe una sola vez, en `run.py`, y el texto la cita desde ahí.
- Evidencia: `src/iif/econ/run.py`, `tests/test_econ.py::test_la_especificacion_publicada_declara_si_el_indice_va_rezagado`. El rezago estimado da +0,00554 (p = 0,38) sin coste muestral: el veredicto no cambia, la descripción sí.
- Estado: cerrada

## B-070 · 2026-09-11 · El denominador del índice era el mismo producto que está en la dependiente
- Contexto: ADR-015 normaliza los montos como porcentaje del producto, que es la definición estándar de profundidad financiera.
- Qué pasó: cinco de las ocho variables del índice llevan el PIB corriente en el denominador y la dependiente es el crecimiento del PIB real per cápita. Un índice placebo con los numeradores congelados en 2018 —sin ninguna información financiera, solo el denominador moviéndose— produce beta = −0,2525 con p = 0,0007 en la especificación publicada. Los coeficientes por dimensión cambian de signo según el denominador: profundidad va de −0,0208 a +0,0104 y uso de −0,0037 a +0,0104.
- Causa raíz: la decisión de normalización se tomó mirando la variable por separado —donde la razón sobre producto es correcta e incuestionable— y no mirando la ecuación completa, donde ese mismo producto aparece al otro lado. La correlación mecánica no es un defecto de la normalización sino de la combinación entre la normalización y la dependiente, y ninguna prueba miraba la combinación.
- Regla: ADR-017. Un denominador que aparece también en la dependiente se rezaga o se fija, y el sesgo se mide con un placebo de solo-denominador que se publica al lado. Regla general nueva: antes de aceptar una normalización, escribir la ecuación final y buscar la misma serie en los dos lados.
- Evidencia: ADR-017, `config/index.yaml` (clave `denominador`), `tests/test_index.py::test_el_placebo_de_solo_denominador_pierde_fuerza_al_rezagar`.
- Estado: cerrada

## B-071 · 2026-09-11 · Un nulo publicado sin su efecto mínimo detectable afirma más de lo que puede
- Contexto: ADR-016 aceptó de antemano que el resultado pudiera ser nulo y decidió publicarlo con su N, sus clústeres y sus pruebas. Se cumplió.
- Qué pasó: el README afirma que el índice no predice el crecimiento. Un contraste que no rechaza no distingue entre que el efecto sea cero y que este diseño no lo vería aunque existiera, y la cifra que separa las dos lecturas —el MDE— no existía en el repositorio. Medida: los efectos fijos de dos vías destruyen el 92 % de la varianza del índice (de 1,2171 a 0,3337), el MDE al 80 % es 0,0167, y el TOST descarta efectos por encima de 0,50 pp por desviación pero no de 0,25 pp.
- Causa raíz: la batería se diseñó contra la correlación espuria, que es el riesgo de un falso positivo, y no contra el falso negativo. Toda la infraestructura mide si un coeficiente distinto de cero es real; ninguna pieza medía si un coeficiente igual a cero es informativo.
- Regla: ADR-018. Un resultado nulo se publica con su MDE y su prueba de equivalencia, y la afirmación del texto es la cota, no la ausencia.
- Evidencia: ADR-018, `src/iif/econ/power.py`, `tests/test_power.py`.
- Estado: cerrada

## B-072 · 2026-09-11 · Tres superficies públicas contradecían al README
- Contexto: ADR-005 adenda 5 retiró el sitio Quarto independiente y dejó la página del portafolio como única superficie pública.
- Qué pasó: `CITATION.cff` seguía apuntando a `financial-inclusion-colombia.vercel.app`, el proyecto que esa misma adenda manda borrar, de modo que quien citara el trabajo obtendría un enlace muerto. `index.qmd` anunciaba la fase 2 en curso y la fase 3 pendiente cuando las dos están hechas y sus resultados publicados. Y el abstract de `README.es.md` decía que todavía no hay resultados, cuarenta y seis líneas antes de publicarlos.
- Causa raíz: las tres son superficies que se escribieron antes de que la fase 3 cerrara y que ninguna prueba recorre. `make check` compila el sitio pero no comprueba que lo que el sitio afirma coincida con lo que el README afirma, y el estado de fase vive escrito a mano en dos sitios distintos (R-15 incumplida sin que nada avise).
- Regla: R-15 aplicada al estado del proyecto: el semáforo de fases tiene una sola fuente. Prueba nueva que recorre las superficies públicas buscando la URL retirada y la contradicción de estado.
- Evidencia: `tests/test_repo.py::test_las_superficies_publicas_no_se_contradicen`.
- Estado: cerrada

## S-020 · 2026-09-11 · La auditoría adversarial encontró lo que doce pruebas sintéticas no podían encontrar
- Contexto: la batería econométrica tiene doce pruebas sobre paneles sintéticos (S-017) que garantizan que cada estimador encuentra lo que hay cuando se sabe lo que hay. Todas pasaban, y aun así cuatro cifras publicadas estaban mal.
- Qué funcionó: atacar el repositorio desde diez ángulos independientes con instrucción de encontrar defectos, y someter cada hallazgo a un refutador con instrucción de tumbarlo. De 67 hallazgos sobrevivieron 57, y diez cayeron —incluidas dos críticas al shift-share que atacaban afirmaciones que ADR-016 nunca hizo, y una lectura del CIPS que era correcta tal como estaba. El refutador importa tanto como el atacante: sin él, la auditoría habría producido una lista de la que un tercio era ruido.
- Por qué funcionó: las pruebas sintéticas validan el estimador contra una verdad conocida, y por eso son ciegas a los errores que están fuera del estimador: el objeto que se le pasa (B-068), la ecuación que el texto describe (B-069), la construcción del regresor aguas arriba (B-070) y la pregunta que el diseño no se hizo (B-071). Ninguno de los cuatro es un fallo de código; los cuatro son fallos de correspondencia entre piezas que por separado funcionan.
- Dónde se reutiliza: la rejilla de 180 especificaciones que salió de la auditoría es ahora `metodologia/especificaciones.qmd`, y el contraste que publica —53 % de las especificaciones significativas sin efectos de tiempo, 7 % con ellos— es la demostración más comunicable que el proyecto tiene. Regla derivada: una batería que solo se prueba contra sí misma no encuentra los errores de correspondencia; hace falta un lector hostil, y se puede fabricar.

## B-073 · 2026-09-11 · La opción `--recalibrar` del índice nunca recalibraba
- Contexto: ADR-015 punto 6 congela los pesos en la ventana de calibración y exige que recalibrar sea una decisión explícita. `iif index --recalibrar` es esa decisión.
- Qué pasó: al cambiar el denominador (ADR-017) y correr `iif index --recalibrar`, las medias y desviaciones de las cinco variables monetarias salieron idénticas a las anteriores, cuando por fuerza tenían que cambiar: la escala de la variable había cambiado.
- Causa raíz: `run()` leía `pesos_congelados` del contrato y se los pasaba a `build_level` **también** cuando `recalibrar` era cierto. Con los pesos dentro, `build_index` toma la rama que los reutiliza y nunca llama a `fit_dimension`, de modo que `res_dep.fits` devolvía exactamente los pesos viejos reconstruidos. La orden se cumplía escribiendo de nuevo los mismos números, y no había forma de notarlo salvo cambiando algo aguas arriba que obligara a los pesos a moverse.
- Regla: una opción que dice reestimar tiene que entrar por el camino que estima. Regla general: cuando una bandera cambia el comportamiento de una función, la prueba compara resultados **distintos**, no que la función devuelva algo.
- Evidencia: `src/iif/index/run.py::run`, `tests/test_index.py::test_recalibrar_vuelve_a_estimar_los_pesos`.
- Estado: cerrada

## B-074 · 2026-09-11 · El placebo por permutación barajaba dentro del año y su nube era tres veces demasiado estrecha
- Contexto: el placebo construye la distribución del coeficiente cuando por diseño no hay nada que encontrar, y es una de las dos piezas que sostienen la inferencia con 33 clústeres.
- Qué pasó: al cambiar el denominador el coeficiente base pasó de +0,00074 a +0,00382, y el placebo pasó a dar p = 0,038 mientras el error agrupado daba p = 0,54 y el bootstrap salvaje p = 0,48. Un placebo que rechaza donde el estimador no rechaza no es un contraste conservador: es un contraste mal especificado, y publicarlo al lado del resultado habría sugerido un efecto que ninguna otra pieza de la batería ve.
- Causa raíz: barajar el índice entre departamentos **dentro de cada año** conserva la trayectoria nacional, que era el objetivo, pero destruye también la correlación serial del índice dentro de cada departamento. El regresor placebo resultante es mucho más ruidoso que el real, su coeficiente mucho más preciso, y la nube mucho más estrecha que el error estándar que el estimador reporta: desviación de 0,00177 contra un SE agrupado de 0,00618.
- Regla: una permutación tiene que destruir exactamente la variación que identifica el efecto y conservar todo lo demás, estructura serial incluida. Permutar la **trayectoria completa** de cada departamento es esa permutación: conserva la trayectoria nacional y la estructura serial, y su nube (0,00542) sí concuerda con el SE agrupado. El modo antiguo se conserva publicado al lado como diagnóstico de cuánta variación destruye cada uno.
- Evidencia: `src/iif/econ/robustness.py::placebo_permutacion` (parámetro `modo`), `tests/test_econ.py::test_el_placebo_por_trayectoria_concuerda_con_el_error_agrupado`.
- Estado: cerrada

## B-075 · 2026-09-11 · El paquete construía la base en un sitio y la leía en otro
- Contexto: `dbt/profiles.yml` resuelve la ruta de DuckDB con `env_var('IIF_DUCKDB_PATH', 'db/iif.duckdb')`, y tanto el Makefile como el flujo de CI definen esa variable. En CI apunta a `/tmp/iif.duckdb`.
- Qué pasó: al añadir una prueba que regenera la batería y la compara contra el JSON publicado, la prueba se saltaba en CI. Tres funciones de Python —`econ.frame.load_frame`, `index.run._con` y `export.atlas`— tenían la ruta escrita a mano como `REPO_ROOT / "db" / "iif.duckdb"` e ignoraban la variable de entorno. En CI, dbt construía la base en `/tmp` y el paquete la buscaba en `db/`, donde no había nada.
- Causa raíz: una constante con dos dueños. dbt tenía su contrato y el paquete tenía el suyo, y como en local los dos caminos coinciden, la discrepancia no se manifestaba nunca. El único escenario que la revelaba —CI con la base fuera del repositorio— no ejecutaba ninguno de los tres comandos.
- Regla: R-15. La ruta de la base vive en `iif.config.DUCKDB_PATH`, con el mismo contrato que `dbt/profiles.yml`, y nadie más la construye. Regla general: cuando una configuración la leen dos herramientas distintas, la segunda no la reescribe, la importa.
- Evidencia: `src/iif/config.py::_duckdb_path`, y el paso «El indice y la bateria corren de punta a punta» de `.github/workflows/ci.yml`, que habría fallado con la ruta vieja.
- Estado: cerrada

## B-076 · 2026-09-11 · El CLI escribía un carácter que la consola de Windows no sabe representar
- Contexto: `iif index` e `iif econ` terminan confirmando por pantalla con `typer.echo(f"✓ {ruta}")`.
- Qué pasó: en una consola de Windows con la página de códigos por defecto (cp1252), el comando completaba su trabajo —el Parquet quedaba escrito— y después moría con `UnicodeEncodeError: 'charmap' codec can't encode character '\u2713'`. El código de salida era 1, de modo que cualquier encadenamiento posterior se detenía por un fallo que ya había ocurrido después del trabajo útil.
- Causa raíz: la salida del programa asume UTF-8 sin declararlo. En Linux y en CI la asunción se cumple y el error no existe; en la máquina del autor, no.
- Regla: R-04 en espíritu, ampliada al entorno: un comando no asume la codificación de la terminal que lo llama. Mientras el carácter se conserve, la variable `PYTHONIOENCODING=utf-8` queda declarada en el flujo de CI y anotada en la guía como requisito para Windows.
- Evidencia: `.github/workflows/ci.yml`, paso «El indice y la bateria corren de punta a punta».
- Estado: abierta — el arreglo de fondo es que `cli.py` fuerce UTF-8 en su salida o use un carácter ASCII; queda anotado y sin hacer para no mezclarlo con esta tanda.

## B-077 · 2026-09-23 · El bootstrap salvaje se studentizaba con el error homocedástico
- Contexto: el bootstrap es la corrección de ADR-016 para 33 clústeres; lo señaló el referee de identificación (informe 01, O2).
- Qué pasó: cada réplica se dividía por `sqrt(e'e/gl · (X'X)^-1)` y no por el error agrupado (CRVE). Con el CRVE, el p del bootstrap de la base pasa de 0,481 a 0,550.
- Causa raíz: se reutilizó el estadístico del MCO homocedástico, y la prueba de tamaño no simulaba heterocedasticidad por clúster.
- Regla: una réplica se studentiza con el mismo estimador de varianza que el estadístico observado, y la prueba de tamaño incluye heterocedasticidad por clúster.
- Evidencia: `src/iif/econ/inference.py`; `tests/test_econ.py::test_el_bootstrap_agrupado_tiene_el_tamano_nominal_con_heterocedasticidad`, `::test_el_crve_del_bootstrap_es_el_agrupado_con_su_correccion`.
- Estado: cerrada

## B-078 · 2026-09-23 · La cota del titular usaba 186 grados de libertad con errores agrupados, y no se sostenía
- Contexto: ADR-018 hizo de la cota de ±0,50 pp la afirmación principal del proyecto.
- Qué pasó: el TOST y el MDE usaban los grados de libertad residuales (186) y no los de 33 clústeres. Con t(32) el TOST a ±0,50 pp da 0,042; con el bootstrap, que es la inferencia de referencia, 0,068. La cota vigente es de unos 0,55 pp por desviación identificante (≈ 2 pp por desviación bruta). El README, el caso de estudio y la página del portafolio afirmaban ±0,50 pp.
- Causa raíz: grados de libertad del MCO en una inferencia agrupada, y un titular que no nombraba la escala de la desviación.
- Regla: con errores agrupados la referencia es t(G − 1); toda cota se publica en las dos escalas (identificante y bruta) y con la inferencia de referencia, y el titular dice cuál.
- Evidencia: ADR-024; `tests/test_resultados_publicados.py::test_la_conclusion_de_la_cota_es_la_que_el_texto_afirma`; README #main-result.
- Estado: cerrada

## B-079 · 2026-09-23 · «No se pueden contrastar tendencias previas» era un artefacto de construcción
- Contexto: ADR-016 lo descartaba en sus alternativas porque la dependiente empezaba en 2019.
- Qué pasó: la exposición está fija en 2018 y el PIB real existe desde 2005. Contrastado, la prueba conjunta de 2006–2018 no se rechaza (p bootstrap 0,41).
- Causa raíz: la muestra de la dependiente se ató a la del índice sin necesidad.
- Regla: una exposición fija no necesita el regresor antes del año base; las tendencias previas se miden con la serie más larga de la dependiente.
- Evidencia: `designs.tendencias_previas`; `resultados.json` → `tendencias_previas`.
- Estado: cerrada

## B-080 · 2026-09-23 · El denominador rezagado reduce el sesgo del placebo pero no lo elimina
- Contexto: ADR-017 cambió al denominador rezagado con un placebo calculado a mano (−0,2525) que no estaba en `resultados.json` (R-09).
- Qué pasó: con los controles de la base, el placebo de solo-denominador da −0,228 (p < 0,001) con el producto contemporáneo, −0,129 (p = 0,030) con el rezagado y +0,129 (p = 0,44) con el fijo. El Granger inverso negativo es la misma mecánica: con el denominador fijo cae a p = 0,27.
- Causa raíz: la prueba sintética de ADR-017 supone un paseo aleatorio sin reversión a la media.
- Regla: el placebo de solo-denominador vive en `resultados.json` con y sin controles; el índice de denominador fijo se publica como coprincipal.
- Evidencia: `src/iif/econ/denominador.py`; `resultados.json` → `denominador`; README #diagnostics.
- Estado: cerrada

## B-081 · 2026-09-23 · La curva escalaba «solo entidad» con la desviación de dos vías
- Qué pasó: los puntos porcentuales de las especificaciones sin efectos de tiempo salían encogidos; la mediana pasa de 0,40 a 0,95 pp.
- Causa raíz: `escala_del_regresor` no conocía el régimen de efectos fijos.
- Regla: la escala identificante es la de su propio régimen de efectos fijos.
- Evidencia: `tests/test_curve.py::test_solo_entidad_se_escala_con_su_propia_desviacion`.
- Estado: cerrada

## B-082 · 2026-09-23 · El texto describía un placebo, un modelo espacial y un diseño que el código no hace
- Qué pasó: `panel.qmd` decía «barajado dentro de cada año» y mostraba el p por trayectoria (B-074); README y `panel.qmd` anunciaban SAR/SDM, un evento de corresponsales digitales e interacciones que no se estiman; el «shift-share» es un diseño de exposición inicial; el README decía «sin Bogotá +0,000» cuando ese valor es sin Vichada (sin Bogotá es +0,003); el cuadrático no se publicaba.
- Causa raíz: la prosa se escribió a mano y no se regeneró al cambiar el código.
- Regla: la prosa que afirma un resultado se condiciona al JSON o se ata con una prueba; un método que se anuncia tiene su función.
- Evidencia: `metodologia/panel.qmd`; README #method, #main-result.
- Estado: cerrada

## B-083 · 2026-09-23 · La curva cambió con el Sarma corregido y la prueba nueva lo detectó
- Contexto: la prueba `test_la_curva_publicada_coincide_con_su_json` se añadió en esta misma sesión.
- Qué pasó: tras ADR-025, la curva pasó de 49 a 50 de 80 especificaciones significativas sin efectos de tiempo, y la prueba falló en los dos README y en los dos casos de estudio hasta actualizarlos.
- Causa raíz: el conteo de la curva estaba copiado en cuatro textos.
- Regla: las cifras de la curva se leen del JSON en la prueba, nunca se fijan como literales.
- Evidencia: `tests/test_repo.py::test_la_curva_publicada_coincide_con_su_json`.
- Estado: cerrada

## B-084 · 2026-09-23 · La página pública del proyecto contradecía al repositorio
- Contexto: la página vive en otro repositorio (el portafolio) y copiaba las cifras a mano.
- Qué pasó: publicaba β = +0,0007 (p = 0,90), bootstrap 0,89, «91 pruebas», «15 especificaciones», KMO invertidos y el titular «Publiqué el cero», todos anteriores a ADR-017 y ADR-018.
- Causa raíz: dos repositorios con la misma cifra y ninguna prueba que los compare.
- Regla: las cifras del portafolio viven en un solo módulo (`lib/data/thesis-results.ts`) con el archivo y la clave de origen de cada una, y se actualizan en el mismo cierre que cambia `resultados.json`.
- Evidencia: repositorio del portafolio, FALLO-40.
- Estado: cerrada

## B-085 · 2026-09-23 · La distancia tipo Sarma inventaba faltantes y movía su techo
- Contexto: B-064; informe del economista macro (punto 1.5).
- Qué pasó: `_sarma` hacía `fillna(0)` (264 filas con valor frente a 260 del compuesto) y dividía por el máximo de todo el panel, así que añadir un año movía los anteriores.
- Causa raíz: la fórmula se implementó sin mirar R-13 ni la regla de pesos congelados de ADR-004.
- Regla: R-13 y R-11; todo parámetro de escala de un índice se congela en la ventana de calibración.
- Evidencia: ADR-025; `tests/test_index.py::test_sarma_deja_faltante_lo_que_falta`, `::test_sarma_congela_el_techo_en_la_calibracion`. Spearman con el compuesto pasa de 0,899 a 0,859.
- Estado: cerrada

## B-086 · 2026-09-23 · La correlación de rangos agrupada ocultaba el desacuerdo entre versiones del índice
- Qué pasó: se publicaba solo la correlación agrupada, que la tendencia común infla. Con el tipo Sarma corregido la agrupada es 0,86 pero en cambios es 0,45.
- Causa raíz: una sola medida de concordancia para un índice en panel.
- Regla: la concordancia entre versiones de un índice en panel se publica también dentro de cada año y en cambios.
- Evidencia: `data/processed/indice_correlacion_rangos_detalle.csv`; `tests/test_index.py::test_correlacion_de_rangos_distingue_tendencia_comun_de_orden`.
- Estado: cerrada

## B-087 · 2026-09-23 · La tabla de ADR-022 no cuadraba con la salida y medía otro ancho
- Qué pasó: ADR-022 citaba anchos de 2,5, 3,3, 6,2 y 17,5 pp; la salida da 4,3, 4,9, 7,4 y 18,7. Además, a 2 y 3 años el ancho publicado era el del nivel acumulado y el mapa pinta crecimiento anual.
- Causa raíz: el ADR se escribió sobre una corrida anterior sin prueba que atara sus cifras, y `ancho_pp` salía de la varianza del nivel.
- Regla: R-09; un ancho publicado declara de qué variable es, y las cifras de un ADR se atan a la salida con una prueba.
- Evidencia: adenda de ADR-022; `tests/test_forecast.py::test_las_cifras_de_adr_022_cuadran_con_resultados_json`; campos `intervalo_ancho_crecimiento_pp` e `intervalo_ancho_nivel_pp`.
- Estado: cerrada

## B-088 · 2026-09-23 · La cobertura del intervalo existía en código y no se publicaba
- Causa raíz: `cobertura_intervalo` se añadió sin engancharla en `run.construir`.
- Regla: todo ancho de intervalo publicado lleva su cobertura empírica al lado.
- Evidencia: `puerta_de_calidad.cobertura_intervalo_empirica` = 0,814 al 80 % nominal.
- Estado: cerrada

## B-089 · 2026-09-23 · El ancla nacional estaba vencida y nada lo decía
- Qué pasó: el WEO usado tiene corte 2025-05-15, 16,3 meses al cierre.
- Causa raíz: el ancla no tenía fecha de caducidad.
- Regla: un ancla con más de 6 meses avisa al correr y lo deja escrito en la salida.
- Evidencia: `forecast/anchor.py::vigencia`; `ancla.antiguedad_meses` y `ancla.vencida` en `resultados.json`; `tests/test_forecast.py::test_el_ancla_vieja_avisa_y_lo_deja_escrito`.
- Estado: aviso cerrado; la transcripción de la EME de Banrep en `config/forecast.yaml` queda a cargo del autor (hecha el 2026-09-25 con la EME de julio de 2026: B-091)

## B-090 · 2026-09-23 · La proyección se leía como pronóstico
- Qué pasó: la salida no decía que la proyección es la inercia de cada departamento desplazada por un ancla común (desplazamiento 2026 entre −0,863 y −0,821 pp), y ADR-019 medía la ventaja a 2 y 3 años frente a la deriva con la inferencia que ADR-023 invalidó.
- Regla: se publica como escenario condicional al ancla, con el rango del desplazamiento y sin tablas de posiciones.
- Evidencia: `escenario` y `reconciliacion` en `data/processed/forecast/resultados.json`; adenda de ADR-019.
- Estado: cerrada

## S-021 · 2026-09-23 · La frase «el índice mide corresponsales» se volvió cifra
- Contexto: la guía (§9) lo afirmaba sin medirlo.
- Qué funcionó: descomponer la varianza intra de dos vías del compuesto por dimensión: acceso 87,5 %, uso 10,2 %, profundidad 2,3 %.
- Dónde se reutiliza: cualquier índice compuesto que entre a un panel con efectos fijos; `data/processed/indice_varianza_intra.csv`.

## B-091 · 2026-09-25 · El ancla automática estaba congelada y se fechaba por el intermediario
- Qué pasó: `anchor.desde_weo` pedía `IMF/WEO:latest` a DBnomics, que redirige a `WEO:2025-04`: DBnomics dejó de actualizar el WEO en abril de 2025. Re-correr `iif forecast` nunca iba a renovar el ancla. Y la fecha de corte salía de `indexed_at`, el día en que DBnomics indexó la serie, no el día en que el FMI la publicó.
- Causa raíz: la fuente automática no se contrastaba con el emisor. La EME, el ancla preferida (ADR-021), no se había transcrito porque `config/forecast.yaml` decía que «solo se publica en PDF». Banrep publica un Excel, y la pregunta por el PIB es trimestral (encuestas de enero, abril, julio y octubre), en la hoja `PIB` del archivo mensual y en `VARIACIONES PIB TRIM.` de la serie histórica.
- Regla: una fuente se fecha por la publicación de su emisor, nunca por la de un intermediario; toda fuente automática se prueba contra esa fecha.
- Evidencia: ancla central transcrita de la EME de julio de 2026 (`config/forecast.yaml`); el respaldo del WEO pasa a la API SDMX del FMI y se fecha por `PUBLICATION_DATE`; adenda 1 de ADR-021; pruebas `test_el_ancla_de_la_eme_*` y `test_el_weo_se_fecha_por_su_publicacion`.
- Estado: cerrada

## B-092 · 2026-09-25 · La cita del ancla no cumplía las condiciones de uso de sus fuentes
- Qué pasó: el aviso legal de Banrep (§2, versión del 2026-06-03) permite reproducir su información estadística si no se altera, se indica la fuente y se menciona la fecha de consulta del portal; la fuente publicada daba el corte de la encuesta, no la fecha de consulta, y no decía que las cifras son expectativas de los analistas y no pronósticos del Banco. La del WEO no nombraba la base, la edición ni el enlace que piden los términos de datos del FMI (vigentes desde el 2024-10-11).
- Causa raíz: `LICENCIAS_DATOS.md` dejó ambas licencias «pendiente de verificar» y la cita se escribió sin leerlas.
- Regla: ninguna fuente se publica con licencia pendiente; la cita se escribe con las condiciones de uso delante.
- Evidencia: `config/forecast.yaml` (fuente con fecha de consulta y «supuesto del proyecto» para 2028), `anchor.desde_weo` (cita con base, edición, enlace y consulta), `docs/LICENCIAS_DATOS.md`.
- Estado: cerrada; queda abierta la duda de si la EME cae en la §2 o en la §6 del aviso de Banrep (ver licencias)

## B-093 · 2026-09-25 · El README decía que el atlas no pintaba la proyección cuando ya la pintaba
- Contexto: la fila de la proyección en «What exists and what is missing» / «Qué hay y qué falta».
- Qué pasó: la capa 2026–2028 llegó al atlas del portafolio (D-36 del portafolio, verificada en producción), pero los dos README seguían diciendo que el atlas interactivo aún no la pintaba.
- Causa raíz: el cambio se hizo en otro repositorio y ninguna revisión volvió sobre las páginas de estado de este (misma raíz que B-066).
- Regla: R-16. Un cambio en una superficie pública del proyecto, aunque viva en otro repositorio, cierra con una revisión de la tabla de estado de los dos README.
- Evidencia: README.md y README.es.md, #que-hay-y-que-falta.
- Estado: cerrada
