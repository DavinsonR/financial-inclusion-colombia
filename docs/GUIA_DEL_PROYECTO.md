# Guía del proyecto

Documento de control del autor. Se lee una vez de arriba abajo y después se consulta por sección. Fecha: 2026-09-06. Se actualiza al cierre de cada sesión (R-16 en CLAUDE.md). La memoria de errores está en `docs/BITACORA_AGENTE.md`; las decisiones, en `docs/decisiones/`.

## 1. Qué se construye y por qué

El punto de partida es el trabajo de grado (Maestría en Economía, Javeriana, 2026): un índice compuesto de inclusión financiera por departamento y un panel 2017 a 2021. **Ese trabajo es el borrador y la inspiración; sus resultados no se reutilizan ni se publican aquí** (decisión del autor, 2026-09-06). El proyecto rehace todo desde las fuentes.

Lo que se construye es un warehouse dimensional con todas las fuentes públicas (SFC 2017 a 2025 más puntos de atención mensuales, DANE 2005 a 2026, MinTIC, MEN, MGN 2024), un índice de inclusión financiera en dos etapas con pesos congelados y publicados por variable, dos paneles anuales (departamental 2018 a 2025 y municipal 2018 a 2024), un atlas interactivo por región, dimensión y variable, y una batería explícita contra la correlación espuria. Motor: DuckDB en local, en CI y para el sitio; Snowflake queda como demo posterior (ADR-014).

La auditoría del notebook original sigue viva en la bitácora (B-001 a B-015) porque son lecciones de proceso que el asistente no debe repetir, y el port congelado en `src/iif/legacy/` es lo que permitió descubrir hechos sobre los datos que sí importan (por ejemplo B-031: la fila de total departamental de la SFC no se suma con las municipales). Nada de eso aparece en el README ni en el sitio como resultado.

La expectativa honesta sobre el resultado nuevo: puede volver a ser un nulo. Se publicará igual, con su prueba.

## 2. Estado hoy y semáforo por fase

| Fase | Contenido | Estado al 2026-09-06 | Semáforo |
|---|---|---|---|
| 0 | Reestructura del repo, limpieza y subida de los tres artefactos legados, paquete `iif`, documentos de gobierno, dbt, Quarto, CI | Hecha: S1 a S8 completos | verde |
| 1 | Adquisición de todas las fuentes con manifiesto, crosswalk a DIVIPOLA, staging en largo, empalme 2021Q1 | Hecha: 19 fuentes descargadas con manifiesto (77 MB), parsers DANE/MGN, staging de todas las fuentes en dbt, `dim_municipio`, SFC en largo con mapa bloque-columna, empalme 2021Q1 medido, reconstrucción del panel legado (B-031) | verde |
| 2 | `dim_variable` completa, hechos SFC y DANE, paneles anuales, índice en dos etapas | En curso (F1 a F5) | amarillo |
| 3 | Exportación y atlas OJS; econometría: two-way FE anual, CIPS, cambios del IIF, CCE, placebo, shift-share, eventos, espacial | Pendiente | rojo |
| 4 | Anexo de desagregación temporal, MIDAS como sensibilidad, manuscrito | Pendiente | rojo |

Lo que hay hoy en el repo: las 19 fuentes descargadas en `data/raw/` con `manifest.jsonl`, los Parquet tidy del DANE y del MGN en `data/interim/`, el proyecto dbt completo hasta `int_sfc_geo_long`, el paquete `src/iif/` (`config`, `cli`, `acquire`, `parse`, `crosswalk`, `data`, `legacy`), el sitio Quarto, CI con publicación en Vercel y los documentos de gobierno. En `data/legacy/`, `notebooks/legacy/` y `docs/legacy/` están los tres artefactos del trabajo de grado, limpios y congelados como insumo histórico y como evidencia de la bitácora; no alimentan ningún resultado.

Lo que no hay todavía: hechos y paneles anuales, mapa columna a variable completo en `dim_variable`, índice nuevo, atlas, econometría nueva. `make check` corre en cero (ruff, pytest, `dbt build` en DuckDB, `quarto render`).

## 3. Mapa del repo

Una línea por entrada. "Toca esto si…" dice cuándo abrir el archivo. Lo marcado (pendiente) aún no existe.

```
CLAUDE.md                     reglas duras; toca esto si una regla cambia (y solo entonces)
README.md                     portada con 7 anclas; toca esto si cambia el resultado principal o la estructura
CITATION.cff                  cómo citar; toca esto si cambia el título o el año
LICENSE                       MIT para el código
pyproject.toml / uv.lock      dependencias; toca esto con `uv add`, nunca a mano
requirements.txt              exportado desde uv para lectores sin uv (pendiente de regenerar)
Makefile                      todos los comandos; toca esto si aparece un paso nuevo
_quarto.yml, *.qmd            sitio (pendiente); toca esto si cambia una página
config/tesis_documento.yaml   cifras del documento de la tesis; toca esto solo si se corrige una errata del documento
config/sources.yaml           fuentes y reglas de descarga (pendiente); toca esto si una fuente cambia de URL
config/index.yaml             dimensiones, variables, ventana de pesos del índice (pendiente)
config/atlas.yaml             contrato de exportación del atlas (pendiente)
data/legacy/                  congelado (R-06); no se toca
data/raw/                     descargas con manifest.jsonl (pendiente); no se edita a mano
data/interim/, data/processed/ Parquet derivado; se regenera, no se edita
db/                           iif.duckdb local, ignorado por git
dbt/                          seeds, staging, intermediate, marts, tests; toca seeds si cambia un mapa
snowflake/                    roles, warehouse, stages, clonación por vintage (pendiente)
src/iif/config.py             rutas del proyecto; toca esto si aparece una carpeta nueva
src/iif/cli.py                comandos `iif`; toca esto si aparece un comando
src/iif/legacy/               port del notebook; no se cambia el modo `notebook`, se extiende el modo `corrected`
src/iif/data/                 scrub y diccionario; toca esto si aparece un artefacto legado nuevo
src/iif/acquire/, crosswalk/  descarga y DIVIPOLA (pendiente)
tests/                        pytest; marca `data` para pruebas que leen data/raw
notebooks/legacy/             congelado (R-06)
docs/GUIA_DEL_PROYECTO.md     este documento
docs/BITACORA_AGENTE.md       errores y aciertos; toca esto antes de arreglar cualquier error (R-10)
docs/decisiones/              ADR-001 a ADR-014; toca esto antes de cambiar una decisión de valor (R-11)
docs/LICENCIAS_DATOS.md       licencias por fuente y qué implican
docs/decisiones-metodologicas.md  decisiones de la versión corregida de la tesis (ago-2026); histórico
docs/legacy/                  dump original y reproducción; se regenera con `make reproduce`
scripts/install_quarto.sh     Quarto por tarball
.github/workflows/            ci.yml: lint, pruebas, dbt, render y publicación de la rama `site` que despliega Vercel
paper/                        PDF tras el depósito institucional; congelado (R-06)
```

## 4. Glosario

- IIF: índice de inclusión financiera. En la tesis, un solo PCA sobre 9 variables con 4 componentes. En el proyecto, un índice en dos etapas.
- PCA en dos etapas: primero un PCA por dimensión (acceso, uso, profundidad) que produce un subíndice cada una; después un PCA o una suma ponderada de los tres subíndices. Permite descomponer el índice por dimensión y por variable, que es lo que pidió el jurado.
- Efectos fijos two-way: modelo de panel con un intercepto por unidad (departamento) y otro por periodo. El de periodo absorbe los choques comunes (pandemia, tendencia nacional de adopción). Es la especificación de referencia.
- Sesgo de Nickell: en un panel dinámico con efectos fijos y T corto, el coeficiente del rezago de la dependiente está sesgado hacia abajo. La aproximación −(1+ρ)/(T−1) vale para AR(1) puro y con el T efectivo, no con filas repetidas.
- Pesaran CD: estadístico de dependencia transversal de los residuos. Un valor de 69 rechaza la independencia con holgura: los departamentos se mueven juntos.
- Driscoll-Kraay: errores estándar robustos a dependencia transversal y serial. En la tesis multiplican el SE clusterizado por 6.
- DIVIPOLA: codificación oficial del DANE. Departamento con 2 dígitos (`dpto_ccdgo`), municipio con 5 (`mpio_ccdgo`, los dos primeros son el departamento). Toda unidad geográfica del warehouse la lleva.
- Vintage / bitemporal: cada descarga es una versión (`pull_id`, `source_updated_at`). Un hecho tiene fecha de referencia y fecha de publicación; `is_current` marca la versión vigente. Necesario porque el DANE revisa toda la serie del PIB cada julio.
- Esquema estrella: tablas de hechos (medidas con claves) rodeadas de dimensiones (departamento, municipio, periodo, entidad, variable, vintage). Modelo de Kimball. Claves naturales, no sustitutas.
- Staging / intermediate / marts: capas de dbt. Staging renombra y tipa una fuente sin lógica; intermediate cruza y empalma; marts son las tablas que se consumen (hechos, dimensiones, paneles de análisis).
- dbt: herramienta que compila SQL con plantillas, ordena las dependencias entre modelos, corre semillas (CSV versionados) y pruebas (unicidad, relaciones, aceptación, pruebas singulares).
- DuckDB: base de datos analítica embebida en un archivo. Lee Parquet directamente. Objetivo de dbt en local y en CI; no cuesta nada.
- Snowflake: warehouse en la nube. Términos que se usan aquí: warehouse virtual (cómputo que se enciende y apaga, tamaño X-Small), crédito (unidad de cobro por cómputo; X-Small consume 1 crédito por hora activa), stage (área de carga de archivos, interna o externa), `COPY INTO` (carga masiva desde un stage a una tabla), `VARIANT` (columna semiestructurada para JSON crudo; se consulta con `FLATTEN`), Time Travel (consultar una tabla como estaba hace N días), clonación (copia lógica sin duplicar almacenamiento: `CREATE SCHEMA marts_v2026_07 CLONE marts`).
- Parquet: formato columnar comprimido. Cada Parquet del repo pesa menos de 45 MB (ADR-003).
- Quarto: generador del sitio y del manuscrito desde `.qmd` con celdas Python. `freeze: auto` guarda resultados para no recalcular en CI.
- Observable JS (OJS): celdas JavaScript reactivas dentro de Quarto. Con ellas se construye el atlas sin servidor.
- TopoJSON: GeoJSON comprimido que comparte fronteras. El MGN simplificado del atlas va en este formato para respetar el presupuesto de 3 MB.
- Chow-Lin / Denton: métodos de desagregación temporal. Reparten un total anual en trimestres usando un indicador trimestral (ITAED) o suavizando. Solo como anexo con advertencias (ADR-010).
- Crosswalk: tabla de correspondencia entre nombres de municipio en la SFC y códigos DIVIPOLA, con normalización de texto y overrides manuales (ADR-007).
- MIDAS: regresión con regresores a mayor frecuencia que la dependiente (inclusión trimestral, PIB anual). Solo como sensibilidad.

## 5. Decisiones de valor

| Decisión | Opciones | Elegida | Coste | Dónde cambiarla |
|---|---|---|---|---|
| Frecuencia de estimación | trimestral con anuales repetidos; anual; trimestral con desagregación | anual | se pierden 3 de 4 filas; T = 8 departamental, 7 municipal | ADR-001; `config/index.yaml` |
| Número de paneles | uno departamental; dos (departamental 2018 a 2025, municipal 2018 a 2024); tres con ITAED | dos, más ITAED como panel trimestral parcial | tres marts en vez de uno | ADR-001; `dbt/models/marts/` |
| Internet en el índice | dentro; fuera; como control | fuera (es infraestructura, no inclusión financiera) | el índice pierde la variable con más cobertura de Bogotá | ADR-004; `config/index.yaml` |
| Regla de retención de componentes | 80 % de varianza; Kaiser; fijo | Kaiser por dimensión, con pesos implícitos publicados | menos varianza explicada declarada | ADR-004; `config/index.yaml` |
| Ventana de pesos | toda la muestra; ventana inicial congelada | ventana inicial (2018 a 2019) congelada | el índice no "aprende" de años posteriores | ADR-004; `config/index.yaml` |
| Escalado del índice | min-max con EPS; estandarización | estandarización (media 0, desviación 1) | pierde la lectura "0 a 1" | ADR-004 |
| Bogotá | dentro de Cundinamarca; separada | separada (33 unidades, como el DANE) | un clúster más, sin municipios | ADR-013; `dbt/seeds/xw_sfc_departamento.csv` |
| Áreas no municipalizadas | descartar; agregar al departamento; conservar con tipo ANM | conservar con `mpio_tipo = ANM` | filas con población pequeña | ADR-013; `dbt/seeds/` |
| Empalme 2021Q1 | promedio; preferir ptgf; preferir kx2f | kx2f, con la diferencia guardada | una ruptura documentada en la serie | ADR-009; `dbt/models/intermediate/` |
| Resultados del trabajo de grado | publicarlos con la reproducción; usarlos como base; no publicarlos | no publicarlos: la tesis es el borrador y todo se rehace | el sitio y el README no muestran ninguna cifra de la tesis; la auditoría queda como bitácora interna | ADR-006 (adenda); `docs/BITACORA_AGENTE.md` |
| Licencia de datos derivados | MIT; CC BY 4.0; CC BY-SA 4.0 | CC BY-SA 4.0, obligada por SFC, MinTIC y MEN | quien reutilice debe compartir igual | ADR-012; `docs/LICENCIAS_DATOS.md` |
| Datos en el repo o en Releases | todo en git; todo fuera; Parquet < 45 MB en git y desborde en Releases | Parquet en git, desborde en Releases | el autor sube los assets a mano | ADR-003; `config/sources.yaml` (`max_file_mb`) |
| DVC | ahora; diferido; nunca | diferido hasta que el desborde supere 5 archivos | sin versionado fino de datos grandes | ADR-003 |
| Motor del warehouse | Snowflake en producción; BigQuery; Databricks; solo DuckDB | solo DuckDB; Snowflake como demo posterior | cero coste; el demo de Snowflake queda pendiente para el portafolio | ADR-014 (adenda); `dbt/profiles.yml` |
| Publicación del sitio | GitHub Pages; Vercel | Vercel desde la rama `site` que construye CI | una sola plataforma con el portafolio; Vercel no compila Quarto, por eso CI renderiza | ADR-005 (adenda); `.github/workflows/ci.yml` |

## 6. Hoja de ruta por fases

Cada fase tiene criterio de entrada y de salida. Las casillas se marcan al cerrar la sesión (R-16).

### Fase 0: reestructura y gobierno
Entrada: la PR anterior del repo fusionada. Salida: `make check` en cero; cero cadenas privadas (nombre legal, rutas locales, propiedades del libro) en `data/`, `notebooks/` y `docs/`; las 7 anclas del README; CI verde.
- [x] S1 `pyproject.toml`, `uv sync`, `.gitignore`, `.gitattributes`, `Makefile`, `scripts/install_quarto.sh`
- [x] S2 `scrub.py`, `dictionary.py`; los tres artefactos limpios en `data/legacy/`, `notebooks/legacy/`, `docs/legacy/`
- [x] S3 `src/iif/legacy/`, `config/tesis_documento.yaml`; `iif reproduce` con 40 filas y 25 discrepancias; pruebas doradas de Tabla 6, KMO, Bartlett y diagnósticos
- [x] S4 `CLAUDE.md`, bitácora, esta guía, ADR-001 a ADR-014, `LICENCIAS_DATOS.md`, README
- [x] S5 dbt: proyecto, `profiles.yml` (duckdb y snowflake), semillas, `stg_legacy__panel_trimestral`, `dim_departamento`, `dim_periodo`; `snowflake/*.sql`
- [x] S6 Quarto: `_quarto.yml`, páginas y stubs `draft: true`; `quarto render` en cero
- [x] S7 CI: `ci.yml` (lint, pruebas, dbt, render y publicación de la rama `site`); `requirements.txt` exportado
- [x] S8 Commit de fase 0 y push

### Fase 1: adquisición, crosswalk y staging
Entrada: fase 0 cerrada. Salida: `iif manifest verify` sin problemas; ningún archivo > 45 MB; ptgf suma 603.232 filas; cobertura del crosswalk por monto ≥ 99,5 % por trimestre y fuente; diferencias del empalme 2021Q1 anotadas en la bitácora; `test_legacy_vs_ptgf` con ≥ 90 % de columnas dentro de 0,5 %.
- [x] S9 `src/iif/acquire/` (soda, dane, mgn), `config/sources.yaml`, pruebas con `requests` simulado
- [x] S10 Descargas pequeñas: DANE (PIB, VA municipal, población, ITAED, Bogotá, ISE, EMMET), MEN, MGN, SFC `vkbt` y `ptgf`; `iif parse dane` y `iif parse mgn` (ISE, EMMET, Bogotá trimestral, retropolación y PIB por actividad nacional descargados pero sin parser todavía)
- [x] S11 Descargas grandes por año: SFC `kx2f` (1.749.411 filas, 5 particiones de 8 a 11 MB) y MinTIC (2.795.052 filas, 8 particiones); nada superó la puerta de 45 MB
- [x] S12 `iif crosswalk derive-blocks` (78 + 90 pares bloque-columna) y `geo-report` (cobertura 100 % por `renglon`, S-009/S-010); staging de las 13 tablas; `dim_municipio`; `int_sfc_geo_long` (ptgf + kx2f); pruebas de totales y del empalme 2021Q1 (B-032, B-033)
- [x] S13 `test_legacy_vs_ptgf`: las nueve variables SFC que usa el notebook se reconstruyen exactamente desde ptgf; el panel es 2 × el total real (B-031). Las 70 columnas restantes del bloque SFC quedan para cuando exista el mapa columna a variable
- [x] S14 Guía y bitácora al día; PR en borrador; propuesta de texto para la tarjeta del portafolio

### Fase 2: índice, marts y atlas
Entrada: hechos de fase 1 verdes en dbt. Salida: índice con pesos implícitos publicados y prueba de signo; `mart_panel_departamento_anual` y `mart_panel_municipio_anual`; exportación del atlas < 3 MB; páginas `atlas/` y `metodologia/indice.qmd` sin `draft`.

### Fase 3: econometría
Entrada: marts de fase 2. Salida: two-way FE anual como base, CIPS, estimación en cambios, CCE, placebo por permutación, shift-share, estudio de eventos, Moran y SAR/SDM, heterogeneidad por interacciones con wild cluster bootstrap; cada tabla del sitio trazada a una prueba; README con el resultado actualizado.

### Fase 4: anexo y manuscrito
Entrada: fase 3. Salida: anexo de desagregación temporal con advertencias, MIDAS como sensibilidad, manuscrito en Quarto con PDF por tectonic.

## 7. Qué puede cambiar el autor y dónde

- `config/*.yaml`: fuentes y URLs (`sources.yaml`), variables y ventana del índice (`index.yaml`), contrato del atlas (`atlas.yaml`), cifras del documento (`tesis_documento.yaml`, solo si el documento cambia).
- `dbt/seeds/*.csv`: mapa `unicap` a DIVIPOLA, regiones, mapa bloque a columna de la SFC, canales, variables y sus reglas de anualización, overrides del crosswalk. Son la única fuente de verdad (R-15); el código los lee, nunca los duplica.
- `docs/decisiones/`: cualquier cambio en la tabla de la sección 5 empieza con un ADR nuevo o con el estado "reemplazada" en el viejo (R-11).
- Lo que no se toca: `data/legacy/`, `notebooks/legacy/`, `paper/`, el modo `notebook` de `src/iif/legacy/`.

## 8. Cómo verificar

- Local: `make setup && make quarto-install && make check`. `check` corre ruff, pytest sin la marca `data`, `dbt build` en DuckDB y `quarto render`. Con datos crudos descargados, `make test-data` añade las pruebas que los leen.
- Auditoría interna (no publicada): `make reproduce` regenera `docs/legacy/reproduccion.md`, que sirve de evidencia para las entradas B-001 a B-015 de la bitácora. Mientras el panel congelado no cambie, el informe no cambia (sha256 en `data/legacy/SHA256SUMS`).
- Limpieza: `tests/test_repo.py::test_no_private_strings_in_published_trees` recorre `data/legacy`, `notebooks` y `docs` con la lista de cadenas privadas de `iif.data.scrub`; debe dar cero.
- Sitio: `_site/index.html`, `_site/datos/fuentes.html` (manifiesto) y `_site/datos/crosswalk.html` (cobertura y empalme) se renderizan con datos reales; el atlas y la metodología aparecen como borrador hasta la fase 3.
- CI: `ci.yml` corre lo mismo que `make check`, publica `_site` como artefacto y, en `main`, lo empuja a la rama `site` que despliega Vercel.

## 9. Preguntas abiertas

Del lado del autor:
- En Vercel, proyecto `inclusion-financiera-colombia`: Settings, Git, Production Branch = `site`. Es el único ajuste manual; CI se encarga del resto.
- Subir a Release cualquier partición que supere 45 MB (arrastrar en el navegador; desde la sesión no se puede, B-023).
- Cuando quiera el demo de Snowflake: cuenta de prueba, usuario con par de claves y los cinco secrets; entonces se recrea el job de CI (ADR-014).

Riesgos que no se maquillan:
- El traslape municipal entre inclusión y valor agregado es de 7 años (2018 a 2024) con un cambio de esquema de la SFC en 2021Q1. El departamental es de 8 años con 2025 preliminar.
- El valor agregado municipal del DANE es una distribución del PIB departamental con indicadores. Si un indicador de reparto correlaciona con presencia bancaria hay endogeneidad mecánica. Leer `DSO-PIB-DEP-MET-001-V8.pdf` antes de usarlo como dependiente; probar variantes.
- El proyecto no publica resultados hasta la fase 3. Un repositorio con mucha infraestructura y ninguna estimación se ve incompleto para un lector apurado; la guía y el README lo dicen sin rodeos.
- El resultado nuevo puede volver a ser un nulo. Se publica igual, con su prueba.
