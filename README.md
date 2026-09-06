# Inclusión financiera y crecimiento regional en Colombia

**Proyecto de investigación reproducible: warehouse abierto de 19 fuentes públicas (2005–2026), índice de inclusión financiera por dimensiones, paneles anuales departamental y municipal, y atlas interactivo.**

Nace del trabajo de grado *Desarrollo Fintech e inclusión financiera como predictores del crecimiento económico regional en Colombia* (Maestría en Economía, Pontificia Universidad Javeriana, 2026; director: Gabriel Penagos Londoño). Ese trabajo es el borrador y la inspiración: aquí no se reutiliza ninguno de sus resultados. Todo se rehace desde las fuentes, con más años, nivel municipal y un diseño que enfrenta de frente la correlación espuria entre inclusión y crecimiento.

Sitio del proyecto: <https://inclusion-financiera-colombia.vercel.app>. Autor: Davirson Novoa Ramírez.

*English summary: see [Abstract](#abstract).*

<a id="status"></a>
## Estado

| Fecha | Hito |
|---|---|
| ago-2026 | Trabajo de grado radicado ante la Dirección de Posgrados |
| sep-2026 | Fase 0: reestructura del repositorio, paquete `iif`, documentos de gobierno, dbt, sitio y CI |
| sep-2026 | Fase 1: las 19 fuentes descargadas con manifiesto, claves DIVIPOLA, staging de las 13 tablas, SFC en largo, empalme 2021Q1 medido |
| en curso | Fase 2: hechos y paneles anuales, índice en dos etapas |
| pendiente | Fase 3: atlas y econometría; Fase 4: anexos y manuscrito |
| nov-2026 (previsto) | Grado |

El plan completo, con semáforo por fase y las decisiones de valor, está en [`docs/GUIA_DEL_PROYECTO.md`](docs/GUIA_DEL_PROYECTO.md).

## Qué construye

1. **Warehouse.** Esquema estrella con vintages en dbt sobre todas las fuentes públicas: Superintendencia Financiera (2017Q4 a 2025Q4, más puntos de atención mensuales desde 2023), DANE (PIB departamental 2005 a 2025, valor agregado municipal 2011 a 2024, población 2005 a 2042, ITAED trimestral), MinTIC, MEN y el Marco Geoestadístico Nacional 2024. Motor: DuckDB en local y CI. Snowflake queda como demo posterior (ADR-014).
2. **Índice.** Índice de inclusión financiera en dos etapas (acceso, uso, profundidad) con pesos congelados y publicados por variable (ADR-004), a nivel departamental y municipal.
3. **Paneles.** Frecuencia anual: departamental 2018 a 2025 y municipal 2018 a 2024; panel trimestral real solo donde el DANE publica actividad trimestral (ITAED) (ADR-001).
4. **Atlas.** Mapa interactivo del índice por región, dimensión y variable en Quarto y Observable JS, sin servidor (ADR-005).
5. **Econometría.** Efectos fijos de entidad y tiempo como base y una batería explícita contra la correlación espuria (ver [Método](#method)).

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
- El panel trimestral del trabajo de grado está congelado en `data/legacy/` como insumo histórico; no se usa para ningún resultado.

Licencias y atribución por fuente: [`docs/LICENCIAS_DATOS.md`](docs/LICENCIAS_DATOS.md). Modelo de datos: [`datos/modelo-de-datos.qmd`](datos/modelo-de-datos.qmd).

<a id="method"></a>
## Método

1. **Frecuencia anual y dos paneles** (ADR-001). El PIB subnacional es anual; ningún valor anual se repite en cuatro trimestres. Panel departamental 2018 a 2025 (33 unidades), panel municipal 2018 a 2024 (unos 1.100), y panel trimestral solo para los 13 departamentos con ITAED. La desagregación temporal (Chow-Lin, Denton) es un anexo con advertencias (ADR-010).
2. **Índice en dos etapas** (ADR-004). Componentes principales por dimensión (acceso, uso, profundidad), subíndices y compuesto; pesos ajustados en la ventana inicial y congelados; estandarización en lugar de min-max; pesos implícitos por variable siempre publicados; pesos iguales y distancia de Sarma como alternativas.
3. **Batería contra la correlación espuria.** Efectos fijos de entidad y tiempo como base; raíz unitaria de panel con dependencia transversal (CIPS); estimación en cambios del índice; efectos correlacionados comunes (CCE); placebo por permutación; shift-share con exposición inicial de 2018; estudio de eventos (Ingreso Solidario 2020, corresponsales digitales); dependencia espacial (Moran, SAR/SDM); heterogeneidad por interacciones con wild cluster bootstrap. Nunca submuestras de pocos clústeres.
4. **Trazabilidad.** Toda cifra publicada traza a una prueba, a una fila del libro de verificación o a un test dbt (R-09).

<a id="main-result"></a>
## Resultado principal

Todavía no hay. Se publica cuando la Fase 3 lo produzca, con la especificación, el N, los clústeres y la prueba que lo respalda. Lo que se publicará, sea cual sea el signo: la tabla de referencia con efectos fijos de entidad y tiempo, los mismos coeficientes bajo cada elemento de la batería, y las versiones departamental y municipal lado a lado.

<a id="diagnostics"></a>
## Diagnósticos

Los que acompañarán a cada estimación: dependencia transversal (Pesaran CD), raíz unitaria con dependencia transversal (CIPS), errores estándar de Driscoll-Kraay frente a clusterizados, Mundlak en lugar de Hausman, Moran sobre residuos, estabilidad de los pesos del índice y adecuación muestral por dimensión (KMO, Bartlett). Cada uno con su prueba en `tests/` o en `dbt/tests/`.

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
│   └── legacy/        panel del trabajo de grado, congelado como insumo histórico
├── db/                iif.duckdb local (ignorado)
├── dbt/               estrella dimensional: seeds, staging, intermediate, marts, tests
├── snowflake/         scripts para el demo posterior (ADR-014)
├── src/iif/           config, cli, acquire, parse, crosswalk, data, legacy (port congelado)
├── tests/             pytest; marca `data` para pruebas que leen descargas
├── docs/              guía, bitácora, decisiones/ (ADR), licencias, legacy/
├── _quarto.yml, *.qmd sitio (Vercel, rama `site` construida por CI)
└── .github/workflows/ ci.yml (lint, pruebas, dbt, render, publicación del sitio)
```

## Documentos

- [`docs/GUIA_DEL_PROYECTO.md`](docs/GUIA_DEL_PROYECTO.md): qué se construye, semáforo por fase, mapa del repo, glosario, decisiones de valor, hoja de ruta, preguntas abiertas.
- [`docs/BITACORA_AGENTE.md`](docs/BITACORA_AGENTE.md): errores (B-001 en adelante) y aciertos (S-001 en adelante) con causa raíz y regla.
- [`docs/decisiones/`](docs/decisiones/README.md): ADR-001 a ADR-014.
- [`docs/LICENCIAS_DATOS.md`](docs/LICENCIAS_DATOS.md): licencia y atribución por fuente.

<a id="que-hay-y-que-falta"></a>
## Qué hay y qué falta

| Pieza | Estado |
|---|---|
| Descargador con manifiesto, 19 fuentes en `data/raw/` (77 MB), parsers DANE y MGN | Hecho |
| dbt: fuentes, staging de las 13 tablas, `dim_departamento`, `dim_municipio`, `dim_periodo`, SFC en largo por bloque, pruebas de totales y de empalme | Hecho |
| Sitio Quarto, CI, publicación en Vercel | Hecho |
| Documentos de gobierno: guía, bitácora, 14 ADR, licencias | Hecho |
| Mapa completo columna a variable, hechos SFC y DANE, paneles anuales | Fase 2, en curso |
| Índice en dos etapas por dimensión | Fase 2, pendiente |
| Atlas interactivo | Fase 3, pendiente |
| Econometría y batería contra la correlación espuria | Fase 3, pendiente |
| Anexo de desagregación temporal, MIDAS, manuscrito | Fase 4, pendiente |
| Demo de Snowflake (mismos modelos dbt, stage, clon por vintage) | Posterior, sin fecha |
| PDF del trabajo de grado | Tras el depósito en el repositorio institucional de la Javeriana |
| Página en el sitio del autor | <https://proyecto-davirson-git.vercel.app/es/research/fintech-inclusion> |

## Cómo citar

Ver [`CITATION.cff`](CITATION.cff). En texto:

> Novoa Ramírez, D. (2026). *Inclusión financiera y crecimiento regional en Colombia: proyecto de investigación reproducible* [código y datos]. <https://github.com/DavinsonR/inclusion-financiera-colombia>

## Licencia

- **Código** (`src/`, `dbt/`, `scripts/`, `tests/`, `notebooks/`): MIT, ver [`LICENSE`](LICENSE).
- **Texto del trabajo de grado** (`paper/`): © 2026 Davirson Novoa Ramírez, todos los derechos reservados hasta el depósito institucional; después, la licencia que fije ese depósito.
- **Datos derivados** (`data/`, marts, `atlas/data/`): CC BY-SA 4.0, obligado por las licencias de SFC, MinTIC y MEN. Atribución por fuente en [`docs/LICENCIAS_DATOS.md`](docs/LICENCIAS_DATOS.md) (ADR-012).
