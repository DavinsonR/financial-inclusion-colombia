# Inclusión financiera y crecimiento regional en Colombia

*[Read in English](README.md)*

**Investigación reproducible: warehouse abierto de 19 fuentes públicas, índice de inclusión financiera por dimensiones, paneles anuales departamental y municipal, atlas interactivo de los 1.123 municipios y batería econométrica completa contra la correlación espuria.**

Tesis de Maestría en Economía, Pontificia Universidad Javeriana (2026; director: Gabriel Penagos Londoño). Pregunta: ¿la inclusión financiera predice el crecimiento de los departamentos una vez descontadas las tendencias nacionales que los mueven a todos a la vez? La respuesta se publica con su especificación, su N, sus clústeres y sus pruebas, sea cual sea el signo.

Página del proyecto: <https://proyecto-davirson-git.vercel.app/es/research/fintech-inclusion>. Autor: Davirson Novoa Ramírez.

*English summary: see [Abstract](#abstract).*

<a id="status"></a>
## Estado

| Fecha | Hito |
|---|---|
| ago-2026 | Tesis radicada ante la Dirección de Posgrados |
| sep-2026 | Fase 0: paquete `iif`, documentos de gobierno, dbt, sitio y CI |
| sep-2026 | Fase 1: las 19 fuentes descargadas con manifiesto, claves DIVIPOLA, staging de las 13 tablas, SFC en largo, empalme 2021Q1 medido |
| sep-2026 | Fase 2: hechos y paneles anuales, índice por dimensiones con pesos publicados |
| sep-2026 | Fase 3: atlas de tres vistas y batería econométrica con sus resultados (ADR-016) |
| pendiente | Fase 4: anexo de desagregación temporal y manuscrito |
| nov-2026 (previsto) | Grado |

El plan completo, con semáforo por fase y las decisiones de valor, está en [`docs/GUIA_DEL_PROYECTO.md`](docs/GUIA_DEL_PROYECTO.md).

## Qué construye

1. **Warehouse.** Esquema estrella con vintages en dbt sobre todas las fuentes públicas: Superintendencia Financiera (2017Q4 a 2025Q4, más puntos de atención mensuales desde 2023), DANE (PIB departamental 2005 a 2025, valor agregado municipal 2011 a 2024, población 2005 a 2042, ITAED trimestral), MinTIC, MEN y el Marco Geoestadístico Nacional 2024. Motor: DuckDB en local, en CI y para el sitio. BigQuery como warehouse en la nube, en su sandbox gratuito y sin tarjeta (`bigquery/`). Snowflake queda como demo posterior (ADR-014).
2. **Índice.** Índice de inclusión financiera por dimensión (acceso, uso, profundidad) sobre ocho variables normalizadas, con pesos congelados en la ventana de calibración y publicados variable a variable, a nivel departamental y municipal (ADR-004, ADR-015).
3. **Paneles.** Frecuencia anual: departamental 2018 a 2025 y municipal 2018 a 2024; panel trimestral real solo donde el DANE publica actividad trimestral (ITAED) (ADR-001).
4. **Atlas.** Mapa interactivo del índice por región, dimensión y variable, en tres vistas —plano, relieve y municipios— dentro de la página del proyecto; los datos salen de `uv run iif atlas` (ADR-005).
5. **Econometría.** Efectos fijos de entidad y tiempo como base, diagnósticos medidos, cuatro diseños que no dependen de la exogeneidad del índice y bootstrap salvaje por clúster; todo en `src/iif/econ` y publicado en `metodologia/panel.qmd` (ADR-016).

<a id="abstract"></a>
## Abstract

Does financial inclusion predict regional economic growth in Colombia, once national trends are taken out of the picture? This project rebuilds the question from primary sources instead of reusing a thesis. It assembles an open dimensional warehouse of 19 public sources (financial supervisor, national statistics office, ICT and education ministries, 2005 to 2026), resolves every series to DIVIPOLA municipal codes, builds a two-stage financial-inclusion index by dimension with frozen and published weights, and estimates annual panels at department (2018 to 2025) and municipality (2018 to 2024) level with two-way fixed effects plus a battery of tests for spurious correlation (cross-sectional dependence, common correlated effects, permutation placebos, shift-share exposure, event study, spatial dependence). Every published figure traces to a test. No results are published yet: they appear when phase 3 produces them, together with the code that produced them.

## Pregunta de investigación

¿La inclusión financiera predice el crecimiento económico de los departamentos y municipios colombianos una vez descontadas las tendencias nacionales que mueven a todos a la vez?

Un rezago del índice ordena la relación en el tiempo; **no** constituye una estrategia de identificación causal. El lenguaje del proyecto es de predicción, salvo en los diseños (shift-share, estudio de eventos) que sí buscan variación plausiblemente exógena.

<a id="data"></a>
## Datos

Diecinueve fuentes, todas verificadas en línea con URL, filas y licencia, descargadas por `iif acquire` y registradas en `data/raw/manifest.jsonl` con sha256, fecha de la fuente y filas:

| Fuente | Grano | Frecuencia | Cobertura | Licencia |
|---|---|---|---|---|
| SFC `ptgf-ywrb` inclusión financiera (legado) | entidad × municipio × bloque | trimestral | 2017Q4–2021Q1 | CC BY-SA 4.0 |
| SFC `kx2f-xjdq` inclusión financiera (vigente) | entidad × municipio × bloque | trimestral | 2021Q1–2025Q4 | CC BY-SA 4.0 |
| SFC `vkbt-desu` puntos de atención | entidad × municipio × canal | mensual | 2023-01 en adelante | CC BY-SA 4.0 |
| DANE PIB departamental (3 cuadros), por actividad, retropolación | departamento | anual | 2005–2025pr | pública |
| DANE valor agregado municipal | municipio | anual | 2011–2024p | pública |
| DANE población `_VP` | municipio, departamento | anual | 2005–2042 | pública |
| DANE ITAED | 13 departamentos + Bogotá + resto | trimestral | 2015Q1–2026Q1pr | pública |
| DANE PIB trimestral de Bogotá, ISE, EMMET territorial | Bogotá, nacional, dominios | trimestral, mensual | hasta 2026 | pública |
| MinTIC `n48w-gutb` internet fijo | municipio × proveedor | trimestral | 2016Q1–2023Q3 | CC BY-SA 4.0 |
| MEN `nudc-7mev` educación | municipio | anual | 2011–2024 | CC BY-SA 4.0 |
| DANE MGN 2024 | 33 departamentos, 1.121 municipios | sin periodo | sin periodo | pública, se atribuye |

Lo que ya sabemos de los datos, con su prueba:

- Las dos tablas de la SFC llevan el código DIVIPOLA implícito: `renglon` es el código municipal y `999` el total departamental; cobertura del 100 % en los 34 cortes (S-009, S-010).
- La fila de total departamental es la suma exacta de las municipales en la tabla legada; en la vigente difiere hasta 2,2 % en corresponsales desde 2022Q3 (B-032). Nunca se suman ambas.
- El trimestre 2021Q1 existe en las dos tablas: mediana de la diferencia relativa entre ellas 0,02 %, peor departamento 1,8 % (B-033, ADR-009).
- Los ceros de la SFC fuera del bloque de producto, y los ceros de tasas del MEN, son faltantes, no ceros (ADR-008, R-13).
- El panel trimestral anterior está congelado en `data/legacy/`; no alimenta ningún resultado.

Licencias y atribución por fuente: [`docs/LICENCIAS_DATOS.md`](docs/LICENCIAS_DATOS.md). Modelo de datos: [`datos/modelo-de-datos.qmd`](datos/modelo-de-datos.qmd).

<a id="method"></a>
## Método

1. **Frecuencia anual y dos paneles** (ADR-001). El PIB subnacional es anual; ningún valor anual se repite en cuatro trimestres. Panel departamental 2018 a 2025 (33 unidades), panel municipal 2018 a 2024 (unos 1.100), y panel trimestral solo para los 13 departamentos con ITAED. La desagregación temporal (Chow-Lin, Denton) es un anexo con advertencias (ADR-010).
2. **Índice en dos etapas** (ADR-004). Componentes principales por dimensión (acceso, uso, profundidad), subíndices y compuesto; pesos ajustados en la ventana inicial y congelados; estandarización en lugar de min-max; pesos implícitos por variable siempre publicados; pesos iguales y distancia de Sarma como alternativas.
3. **Batería contra la correlación espuria.** Efectos fijos de entidad y tiempo como base; raíz unitaria de panel con dependencia transversal (CIPS); estimación en cambios del índice; efectos correlacionados comunes (CCE); placebo por permutación; shift-share con exposición inicial de 2018; estudio de eventos (Ingreso Solidario 2020, corresponsales digitales); dependencia espacial (Moran, SAR/SDM); heterogeneidad por interacciones con wild cluster bootstrap. Nunca submuestras de pocos clústeres.
4. **Trazabilidad.** Toda cifra publicada traza a una prueba, a una fila del libro de verificación o a un test dbt (R-09).

<a id="main-result"></a>
## Resultado principal

**Con efectos fijos de entidad y tiempo, el índice de inclusión financiera no predice el crecimiento del PIB real per cápita departamental.** Treinta y tres departamentos, 2019 a 2025, N = 228: β = +0,0007 (EE 0,0060, p = 0,90); bootstrap salvaje por clúster p = 0,89; placebo por permutación p = 0,68. Sin efectos de tiempo el mismo coeficiente vale +0,024 con p < 0,001: esa distancia es lo que valía la tendencia nacional.

Las tres dimensiones por separado, la especificación en cambios, el CCE con cargas heterogéneas, el SLX espacial y los índices alternativos por PCA y Sarma dan lo mismo. El único diseño con señal es el shift-share con exposición de 2018 (+0,018, p = 0,007), y la urbanización inicial produce una pendiente igual de significativa: se publica como pendiente diferencial de los departamentos más urbanos, no como efecto del índice.

Todas las cifras salen de `data/processed/econ/resultados.json` (`uv run iif econ`) y se leen en `metodologia/panel.qmd`; el diseño está en ADR-016 y las pruebas sobre paneles sintéticos en `tests/test_econ.py`.

<a id="diagnostics"></a>
## Diagnósticos

| Prueba | Resultado |
|---|---|
| CD de Pesaran sobre los residuos del modelo base | 2,46 (p = 0,014): dependencia transversal débil pero presente; por eso Driscoll-Kraay acompaña al clúster |
| CIPS sobre el índice | −2,28 con T = 8: indicio de estacionariedad, no veredicto |
| I de Moran del crecimiento por año, contigüidad de los arcos del TopoJSON | significativa en 2022 (0,22, p = 0,039) y 2025 (0,23, p = 0,047); el SLX la absorbe |
| Adecuación muestral del índice por dimensión | KMO 0,314 en acceso y 0,404 en uso: por debajo de 0,5, por eso no hay PCA (ADR-015) |

Cada uno con su prueba en `tests/test_econ.py`, `tests/test_index.py` o en `dbt/tests/`.

## Cómo correrlo

```bash
make setup           # uv sync con todos los grupos y kernel de Jupyter
make quarto-install  # Quarto por tarball (sin gh, sin apt)
make acquire         # descarga las 19 fuentes al manifiesto
make parse           # XLSX del DANE y GeoJSON del MGN a Parquet tidy
make check           # ruff + pytest + dbt build (DuckDB) + quarto render
```

Solo `uv`; nunca `pip install`. `make check` corre ruff, pytest, `dbt build` en DuckDB y `quarto render`; `make test-data` añade las pruebas que leen las descargas. Reglas para el asistente: [`CLAUDE.md`](CLAUDE.md).

## Estructura

```
.
├── CLAUDE.md, Makefile, pyproject.toml, uv.lock   reglas, comandos, dependencias
├── config/            sources.yaml (19 fuentes); index, atlas (fase 2)
├── data/
│   ├── raw/           descargas por fuente y año, manifest.jsonl; _large/ ignorado
│   ├── interim/       Parquet tidy del DANE, MGN e informes de claves de la SFC
│   └── legacy/        panel trimestral anterior, congelado; no alimenta ningún resultado
├── db/                iif.duckdb local (ignorado)
├── dbt/               estrella dimensional: seeds, staging, intermediate, marts, tests
├── bigquery/          datasets, carga de Parquet, particionado, control de coste, vistas autorizadas
├── snowflake/         scripts para el demo posterior (ADR-014)
├── src/iif/           config, cli, acquire, parse, crosswalk, index, econ, export, data, legacy
├── tests/             pytest; marca `data` para pruebas que leen descargas
├── docs/              guía, bitácora, decisiones/ (ADR), licencias, legacy/
├── _quarto.yml, *.qmd documentación del proyecto en Quarto (metodología, datos, decisiones)
└── .github/workflows/ ci.yml (lint, pruebas, dbt, render)
```

## Documentos

- [`docs/GUIA_DEL_PROYECTO.md`](docs/GUIA_DEL_PROYECTO.md): qué se construye, semáforo por fase, mapa del repo, glosario, decisiones de valor, hoja de ruta, preguntas abiertas.
- [`docs/BITACORA_AGENTE.md`](docs/BITACORA_AGENTE.md): errores (B-001 en adelante) y aciertos (S-001 en adelante) con causa raíz y regla.
- [`docs/decisiones/`](docs/decisiones/README.md): ADR-001 a ADR-016.
- [`docs/LICENCIAS_DATOS.md`](docs/LICENCIAS_DATOS.md): licencia y atribución por fuente.

<a id="que-hay-y-que-falta"></a>
## Qué hay y qué falta

| Pieza | Estado |
|---|---|
| Descargador con manifiesto, 19 fuentes en `data/raw/` (77 MB), parsers DANE y MGN | Hecho |
| dbt: fuentes, staging de las 13 tablas, `dim_departamento`, `dim_municipio`, `dim_periodo`, SFC en largo por bloque, pruebas de totales y de empalme | Hecho |
| Sitio Quarto y CI (el sitio compila en `make check`; no se publica aparte, ADR-005) | Hecho |
| Documentos de gobierno: guía, bitácora, 14 ADR, licencias | Hecho |
| Diccionario de las 98 variables de la SFC con su regla de anualización | Hecho |
| Hechos de inclusión (trimestral y anual, municipal y departamental), puntos de atención, actividad, internet y educación | Hecho |
| Paneles anuales: departamental 2018-2025 y municipal 2018-2024 | Hecho |
| Índice por dimensión con pesos congelados y publicados, y sus dos versiones de sensibilidad | Hecho |
| Atlas interactivo de tres vistas, dentro de la página del proyecto | Hecho |
| Econometría: `src/iif/econ`, 12 pruebas sintéticas, `metodologia/panel.qmd` con los resultados | Hecho |
| Anexo de desagregación temporal, MIDAS, manuscrito | Fase 4, pendiente |
| BigQuery: objetivo dbt, carga, particionado, control de coste y vistas autorizadas | Escrito; sin ejecutar contra un proyecto real |
| Demo de Snowflake (mismos modelos dbt, stage, clon por vintage) | Posterior, sin fecha |
| PDF de la tesis | Tras el depósito en el repositorio institucional de la Javeriana |
| Página pública, la única | <https://proyecto-davirson-git.vercel.app/es/research/fintech-inclusion> |

## Cómo citar

Ver [`CITATION.cff`](CITATION.cff). En texto:

> Novoa Ramírez, D. (2026). *Inclusión financiera y crecimiento regional en Colombia: proyecto de investigación reproducible* [código y datos]. <https://github.com/DavinsonR/financial-inclusion-colombia>

## Licencia

- **Código** (`src/`, `dbt/`, `scripts/`, `tests/`, `notebooks/`): MIT, ver [`LICENSE`](LICENSE).
- **Texto del trabajo de grado** (`paper/`): © 2026 Davirson Novoa Ramírez, todos los derechos reservados hasta el depósito institucional; después, la licencia que fije ese depósito.
- **Datos derivados** (`data/`, marts, `atlas/data/`): CC BY-SA 4.0, obligado por las licencias de SFC, MinTIC y MEN. Atribución por fuente en [`docs/LICENCIAS_DATOS.md`](docs/LICENCIAS_DATOS.md) (ADR-012).
