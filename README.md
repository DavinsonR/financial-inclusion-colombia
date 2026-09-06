# Inclusión financiera y crecimiento regional en Colombia

**Datos, índice compuesto, econometría de panel y atlas reproducibles (2017–2025)**

Origen: trabajo de grado *Desarrollo Fintech e inclusión financiera como predictores del crecimiento económico regional en Colombia: evidencia de panel departamental con índice compuesto multidimensional (2017–2021)* · Maestría en Economía · Pontificia Universidad Javeriana (Bogotá)
Autor: Davirson Novoa Ramírez · Director: Gabriel Penagos Londoño, Pontificia Universidad Javeriana

Sitio del proyecto (en construcción, GitHub Pages): <https://davinsonr.github.io/inclusion-financiera-colombia/>. El repositorio se renombrará a `inclusion-financiera-colombia`; el nombre actual redirige.

*English summary: see [Abstract](#abstract).*

<a id="status"></a>
## Estado

| Fecha | Hito |
|---|---|
| may-2026 | Proyecto de investigación enviado al director |
| jul-2026 | Concepto del jurado evaluador recibido |
| ago-2026 | Versión corregida radicada ante la Dirección de Posgrados, con las correcciones avaladas por el director |
| sep-2026 | Reestructura del repo como proyecto de investigación reproducible: notebook, panel y resultados publicados y limpios; reproducción con tabla de discrepancias; paquete `iif`; documentos de gobierno |
| nov-2026 (previsto) | Grado |

La tesis está calificada y aprobada. Su resultado central, un nulo bajo efectos fijos de entidad y tiempo, se mantiene. Lo que cambia es el repositorio: deja de ser el depósito de una tesis y pasa a ser un proyecto que la reproduce con honestidad y la extiende. Ver [Qué hay y qué falta](#que-hay-y-que-falta).

## Qué es este repositorio ahora

Cinco piezas, en este orden de construcción:

1. **Reproducción.** El notebook consolidado, el panel trimestral y el dump de resultados de la tesis, limpios de metadatos personales y congelados con sha256. Un port en `src/iif/legacy/` los vuelve a correr y compara cada cifra con la del documento (`docs/legacy/reproduccion.md`).
2. **Warehouse.** Esquema estrella con vintages en dbt sobre todas las fuentes públicas (SFC 2017Q4 a 2025Q4, DANE, MinTIC, MEN, MGN 2024). DuckDB en local y CI; Snowflake como producción (ADR-014).
3. **Índice.** Índice de inclusión financiera en dos etapas (acceso, uso, profundidad), pesos congelados y publicados por variable (ADR-004).
4. **Atlas.** Mapa interactivo por región, dimensión y variable en Quarto y Observable JS, sin servidor (ADR-005).
5. **Econometría.** Paneles anuales departamental (2018 a 2025) y municipal (2018 a 2024), two-way FE como base y una batería contra la correlación espuria (ADR-001).

Hoy está hecha la pieza 1 y el esqueleto de las demás. El plan completo, con semáforo por fase, está en [`docs/GUIA_DEL_PROYECTO.md`](docs/GUIA_DEL_PROYECTO.md).

## Resumen

Texto del trabajo de grado. Las notas de la reproducción están más abajo, en [Datos](#data) y [Resultado principal](#main-result).

Este trabajo pregunta si el desarrollo fintech y la inclusión financiera predicen el crecimiento económico regional en Colombia. Construye un índice compuesto multidimensional de inclusión financiera (IIF) por departamento mediante análisis de componentes principales y lo lleva a un panel departamental para el periodo 2017–2021, con el crecimiento del PIB real per cápita departamental como variable dependiente principal.

El hallazgo central se presenta sin maquillaje: bajo la especificación de referencia, efectos fijos de entidad y de tiempo, el coeficiente del índice **no es estadísticamente significativo** (β = −0,15; p = 0,984). En el modelo estático sin el rezago del crecimiento el coeficiente sí es significativo, con una magnitud cercana a la mitad. El trabajo documenta por qué la especificación exigente es la que manda, cuantifica el sesgo de Nickell del panel dinámico y explica por qué un GMM dinámico no ofrece una alternativa superior con esta dimensión temporal.

<a id="abstract"></a>
## Abstract

Does fintech development and financial inclusion predict regional economic growth in Colombia? This master's thesis builds a multidimensional composite index of financial inclusion (IIF) at the department level through principal component analysis and takes it to a department-level panel for 2017–2021, with the growth of real GDP per capita as the main dependent variable.

The headline result is reported as it is: under the reference specification, two-way fixed effects (entity and time), the index coefficient is **not statistically significant** (β = −0.15; p = 0.984). In the static model without the lagged growth term the coefficient is significant, at roughly half the magnitude. The thesis explains why the demanding specification is the one that rules, quantifies the Nickell bias of the dynamic panel, and shows why a dynamic GMM estimator is not a superior alternative at this time dimension.

Reproduction note (September 2026): re-running the published notebook gives β = +0.36 (p = 0.95, N = 396) under two-way fixed effects, the same null. The thesis panel repeated annual GDP across quarters, so the effective sample is 165 department-years, not 462 rows. Document and code differ in 25 verified figures; see `docs/legacy/reproduccion.md`. The project now rebuilds the data at annual frequency for 2018–2025.

## Pregunta de investigación

¿El desarrollo fintech y la inclusión financiera, medidos con un índice compuesto multidimensional, predicen el crecimiento económico de los departamentos colombianos?

Un rezago del índice ordena temporalmente la relación; **no** constituye una estrategia de identificación causal. El lenguaje del documento es de predicción, no de causalidad.

<a id="data"></a>
## Datos

Panel de la tesis, tal como está congelado en `data/legacy/`:

| Elemento | Valor |
|---|---|
| Unidad | 33 departamentos (Bogotá separada, como el DANE) |
| Filas | 462 = 33 × 14 trimestres, 2017Q4 a 2021Q1, 102 columnas |
| Grano real | Las series financieras (SFC, columnas 7 a 82) son trimestrales. PIB, población, internet, educación, IPC y empleo (columnas 85 a 101) son anuales y están repetidas en los cuatro trimestres de cada año |
| Variable dependiente | Crecimiento del PIB real per cápita departamental: 5 valores anuales por departamento, no 14. El 64,3 % de sus diferencias intra-anuales es cero |
| N efectivo | 165 departamento-años (33 × 5). T = 14 trimestres de datos financieros, T = 5 años de PIB |
| Robustez | PIB agregado departamental |
| Niveles SFC | Valen el doble del dato de la Superintendencia: el panel sumó las filas municipales y la fila de total departamental (`renglon = 999`) de `ptgf-ywrb`. Reconstrucción exacta en `tests/test_legacy_vs_ptgf.py` (B-031). Las log-diferencias y el PCA no cambian; las razones flujo/PIB sí |
| Regresor de interés | IIF_Multidim, índice compuesto de inclusión financiera (PCA, 4 componentes) |

Dicho sin rodeos: la tesis estimó un panel trimestral cuya variable dependiente solo cambia una vez al año. Esa es la razón del nulo bajo efectos fijos de tiempo y del β grande y positivo sin ellos: la correlación es la de dos tendencias nacionales (el índice sube en todos los departamentos; el PIB cae 7,7 % en 2020 y sube 10,6 % en 2021). Detalle en `docs/legacy/reproduccion.md` (diagnóstico D1) y en la bitácora (B-001).

Las fuentes del panel legado se infieren columna a columna en [`data/legacy/diccionario_panel_legacy.csv`](data/legacy/diccionario_panel_legacy.csv) (columna `fuente_estimada`); el notebook no las documentaba. Las fuentes del proyecto nuevo, verificadas en línea con URL, filas y licencia:

| Fuente | Grano | Frecuencia | Cobertura | Licencia |
|---|---|---|---|---|
| SFC `ptgf-ywrb` | entidad × municipio | trimestral | 2017Q4–2021Q1 | CC BY-SA 4.0 |
| SFC `kx2f-xjdq` | entidad × municipio (sin DIVIPOLA) | trimestral | 2021Q1–2025Q4 | CC BY-SA 4.0 |
| SFC `vkbt-desu` puntos de atención | entidad × municipio | mensual | 2023-01 en adelante | CC BY-SA 4.0 |
| DANE PIB departamental | departamento | anual | 2005–2025pr | pública |
| DANE valor agregado municipal | municipio | anual | 2011–2024p | pública |
| DANE población `_VP` | municipio, departamento | anual | 2018–2042 (+2005–2017) | pública |
| DANE ITAED | 13 departamentos + Bogotá | trimestral | 2015Q1–2026Q1pr | pública |
| MinTIC `n48w-gutb` internet fijo | municipio | trimestral | 2017Q2–2023Q3 | CC BY-SA 4.0 |
| MEN `nudc-7mev` educación | municipio | anual | 2011–2024 | CC BY-SA 4.0 |
| DANE MGN 2024 | 33 departamentos, 1.121 municipios | sin periodo | sin periodo | pública, se atribuye |

Cada descarga queda registrada en `data/raw/manifest.jsonl` con sha256, filas, fechas y licencia (fase 1). Licencias y atribución: [`docs/LICENCIAS_DATOS.md`](docs/LICENCIAS_DATOS.md).

<a id="method"></a>
## Método

Método de la tesis, con las notas de la auditoría entre paréntesis:

1. **Índice compuesto (PCA).** IIF_Multidim se construye con análisis de componentes principales sobre 9 variables de acceso, uso y profundidad. Conserva 4 componentes, que explican el 84,4 % de la varianza. (Los pesos implícitos por variable, nunca publicados, dan microcrédito/PIB = −0,231; Kaiser retendría 3 componentes; el escalado min-max más EPS crea un outlier en log(IIF). B-005 a B-007.)
2. **Especificación de referencia.** Panel con efectos fijos de entidad y de tiempo (two-way FE).
3. **Panel dinámico y sesgo de Nickell.** Con ρ̂ = 0,4279 el sesgo se cuantifica y se contrasta con el modelo estático. (La fórmula usó T = 14 trimestres; el T efectivo de la dependiente es 5. El ρ corregido nunca entró en una estimación. B-011.)
4. **Errores estándar y dependencia transversal.** Prueba de Pesaran (CD) y errores estándar de Driscoll-Kraay.
5. **Submuestra prepandemia.** La estimación se repite excluyendo 2020 y 2021.

Las decisiones de la versión corregida de la tesis están en [`docs/decisiones-metodologicas.md`](docs/decisiones-metodologicas.md) (histórico).

Método del proyecto (fases 2 y 3): frecuencia anual con dos paneles (ADR-001); índice en dos etapas con pesos congelados en 2018–2019 y publicados por variable, estandarizado, sin internet (ADR-004); two-way FE como base, raíz unitaria de panel con dependencia transversal (CIPS), estimación en cambios del índice, CCE de Pesaran, placebo por permutación, shift-share con exposición inicial de 2018, estudio de eventos (Ingreso Solidario 2020, corresponsales digitales), dependencia espacial (Moran, SAR/SDM) y heterogeneidad por interacciones con wild cluster bootstrap. Nunca submuestras de 4 clústeres.

<a id="main-result"></a>
## Resultado principal

| Especificación | Coeficiente del IIF | Lectura |
|---|---|---|
| Efectos fijos de entidad y tiempo (referencia, documento de la tesis) | β = −0,15 · p = 0,984 | No significativo |
| Modelo estático sin rezago del crecimiento (documento) | Significativo · magnitud ≈ la mitad | Sensible a la especificación |
| Efectos fijos de entidad y tiempo (reproducción desde el notebook) | β = +0,36 · p = 0,95 · N = 396 | No significativo |
| Efectos fijos solo de entidad, dinámico (reproducción) | β = +57,9 · p < 0,001 · N = 396 | Dos tendencias nacionales; desaparece con efectos de tiempo |

La reproducción desde el notebook publicado da β = +0,36 (p = 0,95) con N = 396; el documento y el código divergen en 25 cifras, ver [`docs/legacy/reproduccion.md`](docs/legacy/reproduccion.md). Otras 13 cifras guardadas en el notebook nunca se compararon con el documento; al menos 7 también difieren. La conclusión no cambia: el nulo sobrevive.

Un resultado que no sobrevive la especificación exigente se publica igual. Es el mismo criterio del proyecto [market-data-medallion](https://github.com/DavinsonR/market-data-medallion), donde solo el 11,8 % de las estrategias ganadoras dentro de muestra sobrevivió fuera de muestra: la validación existe para decir que no.

<a id="diagnostics"></a>
## Diagnósticos

Valores de la reproducción (`docs/legacy/reproduccion.md`); entre paréntesis, los del documento cuando difieren.

| Diagnóstico | Valor / tratamiento |
|---|---|
| Sesgo de Nickell | ρ̂ = 0,4279 (modelo agregado), sesgo aproximado −0,11 con T = 14. El T efectivo de la dependiente es 5; la fórmula es de AR(1) puro; β nunca se corrigió (B-011) |
| Dependencia transversal | Pesaran CD = 69,1 (documento: 66,8), p < 0,001. Los departamentos se mueven juntos |
| Errores estándar | Driscoll-Kraay multiplica el SE clusterizado por 6 (5,96 a 37,0); el β dinámico con efectos de entidad deja de ser significativo (p = 0,34) |
| Pandemia | Pre-COVID, efectos de entidad: β = −1,06, p = 0,61 (documento: 0,12) |
| Hausman | χ² = 292,8 (documento: 33,9). Inválido con covarianza clusterizada; Mundlak es la alternativa (B-008) |
| Índice | KMO = 0,719; Bartlett χ² = 2543; 4 componentes, 84,4 % de varianza; PC1 solo como robustez. Pesos implícitos: microcrédito −0,231 (B-005) |
| Heterogeneidad regional | Estimada con 4 a 11 departamentos por región; con menos de 10 clústeres la inferencia no es fiable (B-009) |

## Cómo correrlo

```bash
make setup           # uv sync con todos los grupos y kernel de Jupyter
make quarto-install  # Quarto por tarball (sin gh, sin apt)
make reproduce       # pipeline legado → docs/legacy/reproduccion.md
make check           # ruff + pytest + dbt build (DuckDB) + quarto render
```

Solo `uv`; nunca `pip install`. `make check` corre ruff, 75 pruebas (13 leen datos descargados) de pytest, `dbt build` en DuckDB (127 nodos y pruebas) y `quarto render`; `make test-data` añade las pruebas que leen `data/interim/`. Reglas para el asistente: [`CLAUDE.md`](CLAUDE.md).

## Estructura

```
.
├── CLAUDE.md, Makefile, pyproject.toml, uv.lock   reglas, comandos, dependencias
├── config/            tesis_documento.yaml (cifras del documento); sources, index, atlas (fase 1–2)
├── data/
│   ├── legacy/        panel congelado (xlsx, parquet), diccionario de 102 columnas, SHA256SUMS
│   ├── raw/           descargas con manifest.jsonl (fase 1); _large/ ignorado
│   ├── interim/, processed/   Parquet derivado
├── db/                iif.duckdb local (ignorado)
├── dbt/               estrella dimensional: seeds, staging, intermediate, marts, tests
├── snowflake/         roles, warehouse, stages, clonación por vintage (fase 0)
├── src/iif/           config, cli, legacy (port del notebook), data (scrub, diccionario), acquire, crosswalk
├── tests/             pytest; marca `data` para pruebas que leen data/raw
├── notebooks/legacy/  TESIS_CONSOLIDADO.ipynb, limpio y congelado
├── docs/              guía, bitácora, decisiones/ (ADR), licencias, legacy/ (dump y reproducción)
├── scripts/           install_quarto.sh
├── paper/             PDF tras el depósito institucional
└── _quarto.yml, *.qmd sitio (fase 0)
```

## Documentos

- [`docs/GUIA_DEL_PROYECTO.md`](docs/GUIA_DEL_PROYECTO.md): qué se construye, semáforo por fase, mapa del repo, glosario, decisiones de valor, hoja de ruta, preguntas abiertas.
- [`docs/BITACORA_AGENTE.md`](docs/BITACORA_AGENTE.md): errores (B-001 en adelante) y aciertos (S-001 en adelante) con causa raíz y regla.
- [`docs/decisiones/`](docs/decisiones/README.md): ADR-001 a ADR-014.
- [`docs/LICENCIAS_DATOS.md`](docs/LICENCIAS_DATOS.md): licencia y atribución por fuente.
- [`docs/legacy/reproduccion.md`](docs/legacy/reproduccion.md): reproducción del notebook con la tabla de discrepancias.
- [`docs/decisiones-metodologicas.md`](docs/decisiones-metodologicas.md): decisiones de la versión corregida de la tesis (histórico).

<a id="que-hay-y-que-falta"></a>
## Qué hay y qué falta

| Pieza | Estado |
|---|---|
| Notebook consolidado (`notebooks/legacy/TESIS_CONSOLIDADO.ipynb`) | En el repositorio, limpio y congelado |
| Panel trimestral de la tesis (`data/legacy/`, xlsx y Parquet, diccionario, SHA256SUMS) | En el repositorio |
| Dump de resultados y reproducción con 40 filas de libro y 25 discrepancias (`docs/legacy/`) | En el repositorio |
| Paquete `src/iif/` (config, CLI, scrub, diccionario, port del notebook en modos `notebook` y `corrected`) | En el repositorio; pruebas pendientes |
| Documentos de gobierno (guía, bitácora, 14 ADR, licencias) | En el repositorio |
| Proyecto dbt (DuckDB y Snowflake), sitio Quarto, CI, `requirements.txt` exportado | Fase 0, hecho |
| Descarga con manifiesto de las 17 fuentes pequeñas (DANE, MEN, MGN, SFC `ptgf` y `vkbt`) y parsers DANE/MGN a Parquet | Fase 1, hecho |
| SFC `kx2f` y MinTIC por año, claves DIVIPOLA por `renglon`, staging de las 13 tablas, `dim_municipio`, SFC en largo, empalme 2021Q1 medido | Fase 1, hecho |
| Marts de hechos y paneles anuales, índice en dos etapas, atlas | Fase 2, pendiente |
| Descargas con manifiesto, crosswalk a DIVIPOLA, staging, empalme 2021Q1 | Fase 1, pendiente |
| Índice en dos etapas, marts anuales, atlas | Fase 2, pendiente |
| Econometría nueva | Fase 3, pendiente |
| Anexo de desagregación, MIDAS, manuscrito | Fase 4, pendiente |
| PDF del trabajo de grado | Se publica tras el depósito en el repositorio institucional de la Javeriana |
| Página en el sitio del autor | <https://proyecto-davirson-git.vercel.app/es/research/fintech-inclusion> (su tarjeta afirma "T = 14 periodos"; se reescribe tras esta auditoría) |

## Cómo citar

Ver [`CITATION.cff`](CITATION.cff). En texto:

> Novoa Ramírez, D. (2026). *Desarrollo Fintech e inclusión financiera como predictores del crecimiento económico regional en Colombia: evidencia de panel departamental con índice compuesto multidimensional (2017–2021)*. Trabajo de grado, Maestría en Economía, Pontificia Universidad Javeriana.

## Licencia

- **Código** (`src/`, `dbt/`, `scripts/`, `tests/`, `notebooks/`): MIT, ver [`LICENSE`](LICENSE).
- **Texto del trabajo de grado** (`paper/`): © 2026 Davirson Novoa Ramírez, todos los derechos reservados hasta el depósito institucional; después, la licencia que fije ese depósito.
- **Datos derivados** (`data/`, marts, `atlas/data/`): CC BY-SA 4.0, obligado por las licencias de SFC, MinTIC y MEN. Atribución por fuente en [`docs/LICENCIAS_DATOS.md`](docs/LICENCIAS_DATOS.md) (ADR-012).
