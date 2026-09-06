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

