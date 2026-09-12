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

Does financial inclusion predict regional economic growth in Colombia, once national trends are taken out of the picture? This project rebuilds the question from primary sources instead of reusing a thesis. It assembles an open dimensional warehouse of 19 public sources (financial supervisor, national statistics office, ICT and education ministries, 2005 to 2026), resolves every series to DIVIPOLA municipal codes, builds a two-stage financial-inclusion index by dimension with frozen and published weights, and estimates annual panels at department (2018 to 2025) and municipality (2018 to 2024) level with two-way fixed effects plus a battery of tests for spurious correlation (cross-sectional dependence, common correlated effects, permutation placebos, shift-share exposure, event study, spatial dependence). Every published figure traces to a test. The headline is a bound rather than an absence: the design rules out effects above half a percentage point of annual growth per standard deviation of the index and cannot speak to anything smaller.

## Pregunta de investigación

¿La inclusión financiera predice el crecimiento económico de los departamentos y municipios colombianos una vez descontadas las tendencias nacionales que mueven a todos a la vez?

El regresor de la especificación base es el índice **contemporáneo**; el rezago se construye y se publica al lado (+0,007, p = 0,25), y cuál de los dos corre lo decide `REZAGO_INDICE` en `src/iif/econ/run.py`, que es la única fuente de verdad de esa elección. Ninguno de los dos ordenamientos constituye una estrategia de identificación causal. El lenguaje del proyecto es de predicción, salvo en los diseños (shift-share, estudio de eventos) que sí buscan variación plausiblemente exógena.

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

**Con efectos fijos de entidad y tiempo, este diseño descarta cualquier efecto del índice sobre el crecimiento departamental mayor que medio punto porcentual por desviación típica, y no puede pronunciarse sobre nada menor.** Treinta y tres departamentos, 2019 a 2025, N = 228: β = +0,0038 (EE 0,0062, p = 0,54); bootstrap salvaje por clúster p = 0,48; placebo por permutación p = 0,51. Sin efectos de tiempo el mismo coeficiente vale +0,027 con p < 0,001: esa distancia es lo que valía la tendencia nacional.

La afirmación es una cota y no una ausencia, porque un nulo sin su potencia no distingue entre «no hay efecto» y «este diseño no lo vería» (ADR-018). El efecto mínimo detectable al 80 % de potencia es de 0,58 puntos porcentuales de crecimiento anual por desviación típica identificante del índice; la prueba de equivalencia descarta efectos por encima de ±0,50 pp (p = 0,04) y **no** descarta ±0,25 pp (p = 0,28). La razón está medida, no supuesta: los efectos fijos de dos vías se llevan el 92 % de la varianza del índice, de una desviación de 1,24 a 0,34.

El nulo resiste todo lo que se le ha puesto enfrente. Dejando fuera un departamento cada vez, el coeficiente se mueve entre 0,000 y +0,008 y nunca es significativo; sin Bogotá vale +0,000. Quitando 2020, 2021, 2024 o 2025 sigue nulo. Las tres dimensiones por separado, la especificación en cambios, el CCE con cargas heterogéneas, el SLX espacial y los índices alternativos por PCA y Sarma coinciden.

El único diseño con señal es el shift-share con exposición de 2018 (+0,017, p = 0,005), que sobrevive a su propio bootstrap salvaje (p = 0,007) y a su propio placebo (p = 0,004). No sobrevive al contraste que importa: la urbanización inicial produce por su cuenta una pendiente igual de significativa, y con las dos exposiciones en la misma ecuación el índice cae a p = 0,10. Se publica como pendiente diferencial de los departamentos más urbanos, no como efecto del índice.

Todas las cifras salen de `data/processed/econ/resultados.json` (`uv run iif econ`) y se leen en `metodologia/panel.qmd`; el diseño está en ADR-016 y ADR-018, y las pruebas sobre paneles sintéticos en `tests/test_econ.py` y `tests/test_power.py`.

<a id="diagnostics"></a>
## Diagnósticos

| Prueba | Resultado |
|---|---|
| CD de Pesaran sobre los residuos del modelo base | 2,40 (p = 0,016): dependencia transversal débil pero presente; por eso Driscoll-Kraay acompaña al clúster |
| CIPS sobre el índice | −2,10 con T = 8: por debajo del valor crítico tabulado al 10 %, así que indicio de estacionariedad, no veredicto |
| I de Moran **sobre los residuos** por año, contigüidad de los arcos del TopoJSON | significativa en 2019 (0,26, p = 0,015); el SLX **no** la absorbe (0,25, p = 0,028). Medida sobre el crecimiento crudo los años significativos serían 2022 y 2025: otra pregunta, y la equivocada (B-048) |
| Efecto mínimo detectable y equivalencia | MDE₈₀ = 0,58 pp por desviación identificante; equivalencia a ±0,50 pp, no a ±0,25 pp |
| Adecuación muestral del índice por dimensión | KMO 0,317 en uso y 0,407 en profundidad: por debajo de 0,5, por eso no hay PCA (ADR-015) |
| Placebo de denominador: índice con los numeradores de 2018 congelados | con el producto contemporáneo correlaciona −0,31 con el crecimiento y lo predice; con el producto rezagado la correlación es +0,05 y no lo predice (ADR-017) |

Cada uno con su prueba en `tests/test_econ.py`, `tests/test_power.py`, `tests/test_index.py` o en `dbt/tests/`.

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
- [`docs/decisiones/`](docs/decisiones/README.md): ADR-001 a ADR-018.
- [`docs/LICENCIAS_DATOS.md`](docs/LICENCIAS_DATOS.md): licencia y atribución por fuente.

<a id="que-hay-y-que-falta"></a>
## Qué hay y qué falta

| Pieza | Estado |
|---|---|
| Descargador con manifiesto, 19 fuentes en `data/raw/` (77 MB), parsers DANE y MGN | Hecho |
| dbt: fuentes, staging de las 13 tablas, `dim_departamento`, `dim_municipio`, `dim_periodo`, SFC en largo por bloque, pruebas de totales y de empalme | Hecho |
| Sitio Quarto y CI (el sitio compila en `make check`; no se publica aparte, ADR-005) | Hecho |
| Documentos de gobierno: guía, bitácora, 18 ADR, licencias | Hecho |
| Diccionario de las 98 variables de la SFC con su regla de anualización | Hecho |
| Hechos de inclusión (trimestral y anual, municipal y departamental), puntos de atención, actividad, internet y educación | Hecho |
| Paneles anuales: departamental 2018-2025 y municipal 2018-2024 | Hecho |
| Índice por dimensión con pesos congelados y publicados, y sus dos versiones de sensibilidad | Hecho |
| Atlas interactivo de tres vistas, dentro de la página del proyecto | Hecho |
| Econometría: `src/iif/econ`, pruebas sintéticas de la batería y de la potencia, `metodologia/panel.qmd` con los resultados | Hecho |
| Potencia, equivalencia y curva de especificación (ADR-018) | Hecho |
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
