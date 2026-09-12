# Financial inclusion and regional growth in Colombia

*[Leer en español](README.es.md)*

**Reproducible research: an open warehouse of 19 public sources, a financial-inclusion index by dimension, annual department and municipality panels, an interactive atlas of all 1,123 municipalities, and a full econometric battery against spurious correlation.**

MSc Economics thesis, Pontificia Universidad Javeriana (2026; supervisor: Gabriel Penagos Londoño). The question: does financial inclusion predict departmental growth once the national trends that move every department at once are taken out? The answer is published with its specification, its N, its clusters and its tests, whatever the sign.

Project page: <https://proyecto-davirson-git.vercel.app/en/research/fintech-inclusion>. Author: Davirson Novoa Ramírez.

*Documentación del proyecto (guía, bitácora, ADR, metodología) en español: ver [README.es.md](README.es.md).*

<a id="status"></a>
## Status

| Date | Milestone |
|---|---|
| Aug 2026 | Thesis filed with the graduate school |
| Sep 2026 | Phase 0: the `iif` package, governance documents, dbt, site and CI |
| Sep 2026 | Phase 1: 19 sources downloaded with a manifest, DIVIPOLA keys, staging of the 13 tables, the supervisor's data in long form, the 2021Q1 splice measured |
| Sep 2026 | Phase 2: facts and annual panels, index by dimension with published weights |
| Sep 2026 | Phase 3: a three-view atlas and the econometric battery with its results (ADR-016) |
| pending | Phase 4: temporal-disaggregation annex and manuscript |
| Nov 2026 (expected) | Graduation |

The full plan, with a per-phase status light and the decisions of record, is in [`docs/GUIA_DEL_PROYECTO.md`](docs/GUIA_DEL_PROYECTO.md) (Spanish).

## What it builds

1. **Warehouse.** A star schema with vintages in dbt over every public source: the financial supervisor (2017Q4 to 2025Q4, plus monthly service points from 2023), the statistics office (departmental GDP 2005 to 2025, municipal value added 2011 to 2024, population 2005 to 2042, the quarterly ITAED indicator), the ICT and education ministries, and the 2024 national geostatistical framework. Engine: DuckDB locally, in CI and for the site. BigQuery as the cloud warehouse, in its free sandbox and without a card (`bigquery/`). Snowflake is kept as a later demonstration (ADR-014).
2. **Index.** A financial-inclusion index by dimension (access, use, depth) over eight normalised variables, with weights frozen over the calibration window and published variable by variable, at department and municipality level (ADR-004, ADR-015).
3. **Panels.** Annual frequency: department 2018 to 2025 and municipality 2018 to 2024; a real quarterly panel only where the statistics office publishes quarterly activity (ITAED) (ADR-001).
4. **Atlas.** An interactive map of the index by region, dimension and variable, in three views — flat, raised and municipalities — inside the project page; the data comes from `uv run iif atlas` (ADR-005).
5. **Econometrics.** Entity and time fixed effects as the baseline, diagnostics measured rather than assumed, four designs that do not rely on the index being exogenous, and a wild cluster bootstrap; all in `src/iif/econ` and published in `metodologia/panel.qmd` (ADR-016).

<a id="abstract"></a>
## Abstract

Does financial inclusion predict regional economic growth in Colombia, once national trends are taken out of the picture? This project rebuilds the question from primary sources instead of reusing a thesis. It assembles an open dimensional warehouse of 19 public sources (financial supervisor, national statistics office, ICT and education ministries, 2005 to 2026), resolves every series to DIVIPOLA municipal codes, builds a two-stage financial-inclusion index by dimension with frozen and published weights, and estimates annual panels at department (2018 to 2025) and municipality (2018 to 2024) level with two-way fixed effects plus a battery of tests for spurious correlation (cross-sectional dependence, common correlated effects, permutation placebos, shift-share exposure, event study, spatial dependence). Every published figure traces to a test. The headline is a bound rather than an absence: the design rules out effects above half a percentage point of annual growth per standard deviation of the index and cannot speak to anything smaller.

## Research question

Does financial inclusion predict the economic growth of Colombian departments and municipalities once the national trends that move them all at once are taken out?

The baseline regressor is the **contemporaneous** index; the lag is built and published beside it (+0.007, p = 0.25), and which of the two runs is decided by `REZAGO_INDICE` in `src/iif/econ/run.py`, the single source of truth for that choice. Neither ordering constitutes a causal identification strategy. The project's language is predictive, except in the designs (shift-share, event study) that do look for plausibly exogenous variation.

<a id="data"></a>
## Data

Nineteen sources, all verified online with URL, row count and licence, downloaded by `iif acquire` and recorded in `data/raw/manifest.jsonl` with a sha256, the source date and the row count:

| Source | Grain | Frequency | Coverage | Licence |
|---|---|---|---|---|
| Financial supervisor `ptgf-ywrb`, financial inclusion (legacy) | institution × municipality × block | quarterly | 2017Q4–2021Q1 | CC BY-SA 4.0 |
| Financial supervisor `kx2f-xjdq`, financial inclusion (current) | institution × municipality × block | quarterly | 2021Q1–2025Q4 | CC BY-SA 4.0 |
| Financial supervisor `vkbt-desu`, service points | institution × municipality × channel | monthly | 2023-01 onwards | CC BY-SA 4.0 |
| Statistics office, departmental GDP (3 tables), by activity, backcast | department | annual | 2005–2025p | public |
| Statistics office, municipal value added | municipality | annual | 2011–2024p | public |
| Statistics office, population `_VP` | municipality, department | annual | 2005–2042 | public |
| Statistics office, ITAED | 13 departments + Bogotá + rest | quarterly | 2015Q1–2026Q1p | public |
| Statistics office, Bogotá quarterly GDP, ISE, territorial EMMET | Bogotá, national, domains | quarterly, monthly | to 2026 | public |
| ICT ministry `n48w-gutb`, fixed internet | municipality × provider | quarterly | 2016Q1–2023Q3 | CC BY-SA 4.0 |
| Education ministry `nudc-7mev` | municipality | annual | 2011–2024 | CC BY-SA 4.0 |
| National geostatistical framework 2024 | 33 departments, 1,121 municipalities | no period | no period | public, attributed |

What we already know about the data, each with its test:

- The supervisor's two tables carry the DIVIPOLA code implicitly: `renglon` is the municipal code and `999` the departmental total; 100% coverage across the 34 quarterly cuts (S-009, S-010).
- The departmental total row is the exact sum of the municipal ones in the legacy table; in the current one it diverges by up to 2.2% on banking correspondents from 2022Q3 (B-032). The two are never added together.
- Quarter 2021Q1 exists in both tables: the median relative difference between them is 0.02%, and the worst department 1.8% (B-033, ADR-009).
- The supervisor's zeros outside the product block, and the education ministry's zero rates, are missing values, not zeros (ADR-008, R-13).
- The previous quarterly panel is frozen in `data/legacy/`; it feeds no result.

Licences and attribution per source: [`docs/LICENCIAS_DATOS.md`](docs/LICENCIAS_DATOS.md). Data model: [`datos/modelo-de-datos.qmd`](datos/modelo-de-datos.qmd).

<a id="method"></a>
## Method

1. **Annual frequency and two panels** (ADR-001). Subnational GDP is annual; no annual value is ever repeated across four quarters. A department panel 2018 to 2025 (33 units), a municipal panel 2018 to 2024 (about 1,100), and a quarterly panel only for the 13 departments with ITAED. Temporal disaggregation (Chow-Lin, Denton) is an annex with caveats (ADR-010).
2. **A two-stage index** (ADR-004, ADR-015). Subindices by dimension (access, use, depth) and a composite; weights fitted over the initial window and frozen; standardisation rather than min-max; implicit weights per variable always published; PCA and Sarma's distance as alternatives. Amounts are normalised by the **lagged** product, not the contemporaneous one: the same GDP sits in the dependent variable, and dividing by it manufactures correlation (ADR-017).
3. **A battery against spurious correlation.** Entity and time fixed effects as the baseline; panel unit root with cross-sectional dependence (CIPS); estimation in index changes; common correlated effects (CCE); a permutation placebo; shift-share with 2018 initial exposure; an event study (Ingreso Solidario 2020, digital correspondents); spatial dependence (Moran, SAR/SDM); heterogeneity through interactions with a wild cluster bootstrap. Never subsamples with few clusters.
4. **Traceability.** Every published figure traces to a test, a row of the verification ledger, or a dbt test (R-09).

<a id="main-result"></a>
## Main result

**With entity and time fixed effects, this design rules out any effect of the financial-inclusion index on departmental growth larger than half a percentage point per standard deviation — and cannot speak to anything smaller.** Thirty-three departments, 2019 to 2025, N = 228: β = +0.0038 (SE 0.0062, p = 0.54); wild cluster bootstrap p = 0.48; permutation placebo p = 0.51. Without time effects the same coefficient is +0.027 with p < 0.001: that distance is what the national trend was worth.

The statement is a bound, not an absence, because a null without its power does not distinguish "there is no effect" from "this design would not see one" (ADR-018). The minimum detectable effect at 80% power is 0.58 percentage points of annual growth per identifying standard deviation of the index; equivalence testing rules out effects above ±0.50 pp (p = 0.04) and **fails** to rule out ±0.25 pp (p = 0.28). The reason is measured, not asserted: two-way fixed effects remove 92% of the index's variance, from a standard deviation of 1.24 to 0.34.

The null is robust to everything tried against it. Leaving out one department at a time, the coefficient stays between 0.000 and +0.008 and is never significant; without Bogotá it is +0.000. Dropping 2020, 2021, 2024 or 2025 leaves it null. The three dimensions on their own, the specification in changes, CCE with heterogeneous loadings, the spatial SLX and the alternative PCA and Sarma indices all agree.

The only design with a signal is the shift-share with 2018 exposure (+0.017, p = 0.005), which survives its own wild bootstrap (p = 0.007) and its own placebo (p = 0.004). It does not survive the contrast that matters: initial urbanisation produces an equally significant slope on its own, and with both exposures in the same equation the index falls to p = 0.10. It is published as a differential slope for the more urban departments, not as an effect of the index.

Every figure comes from `data/processed/econ/resultados.json` (`uv run iif econ`) and is read in `metodologia/panel.qmd`; the design is in ADR-016 and ADR-018, and the tests over synthetic panels in `tests/test_econ.py` and `tests/test_power.py`.

<a id="diagnostics"></a>
## Diagnostics

| Test | Result |
|---|---|
| Pesaran's CD on the baseline model's residuals | 2.40 (p = 0.016): weak but present cross-sectional dependence; hence Driscoll-Kraay alongside the cluster |
| CIPS on the index | −2.10 with T = 8: below the 10% tabulated critical value, so an indication of stationarity, not a verdict |
| Moran's I **on the residuals** by year, contiguity from the TopoJSON arcs | significant in 2019 (0.26, p = 0.015); the SLX does **not** absorb it (0.25, p = 0.028). Measured on raw growth instead, the significant years would be 2022 and 2025 — a different question and the wrong one (B-048) |
| Minimum detectable effect and equivalence | MDE₈₀ = 0.58 pp per identifying SD; equivalence at ±0.50 pp, not at ±0.25 pp |
| Sampling adequacy of the index by dimension | KMO 0.317 for use and 0.407 for depth: below 0.5, which is why there is no PCA (ADR-015) |
| Denominator placebo: index with 2018 numerators frozen | with the contemporaneous product it correlates −0.31 with growth and predicts it; with the lagged product the correlation is +0.05 and it does not (ADR-017) |

Each with its test in `tests/test_econ.py`, `tests/test_power.py`, `tests/test_index.py` or in `dbt/tests/`.

## How to run it

```bash
make setup           # uv sync with every group, plus the Jupyter kernel
make quarto-install  # Quarto from a tarball (no gh, no apt)
make acquire         # downloads the 19 sources into the manifest
make parse           # statistics-office XLSX and framework GeoJSON into tidy Parquet
make check           # ruff + pytest + dbt build (DuckDB) + quarto render
```

`uv` only; never `pip install`. `make check` runs ruff, pytest, `dbt build` on DuckDB and `quarto render`; `make test-data` adds the tests that read the downloads. Rules for the assistant: [`CLAUDE.md`](CLAUDE.md).

## Layout

```
.
├── CLAUDE.md, Makefile, pyproject.toml, uv.lock   rules, commands, dependencies
├── config/            sources.yaml (19 sources); index, atlas
├── data/
│   ├── raw/           downloads by source and year, manifest.jsonl; _large/ ignored
│   ├── interim/       tidy Parquet from the statistics office, the framework and the supervisor's key reports
│   └── legacy/        the previous quarterly panel, frozen; it feeds no result
├── db/                local iif.duckdb (ignored)
├── dbt/               star schema: seeds, staging, intermediate, marts, tests
├── bigquery/          datasets, Parquet load, partitioning, cost control, authorised views
├── snowflake/         scripts for the later demonstration (ADR-014)
├── src/iif/           config, cli, acquire, parse, crosswalk, index, econ, export, data, legacy
├── tests/             pytest; a `data` mark for tests that read downloads
├── docs/              guide, logbook, decisiones/ (ADRs), licences, legacy/
├── _quarto.yml, *.qmd project documentation in Quarto (method, data, decisions)
└── .github/workflows/ ci.yml (lint, tests, dbt, render)
```

## Documents

These are written in Spanish, the language of the thesis.

- [`docs/GUIA_DEL_PROYECTO.md`](docs/GUIA_DEL_PROYECTO.md): what is being built, a per-phase status light, the repo map, a glossary, the decisions of record, the roadmap and the open questions.
- [`docs/BITACORA_AGENTE.md`](docs/BITACORA_AGENTE.md): mistakes (B-001 onwards) and wins (S-001 onwards) with root cause and rule.
- [`docs/decisiones/`](docs/decisiones/README.md): ADR-001 to ADR-018.
- [`docs/LICENCIAS_DATOS.md`](docs/LICENCIAS_DATOS.md): licence and attribution per source.

<a id="que-hay-y-que-falta"></a>
## What exists and what is missing

| Piece | Status |
|---|---|
| Downloader with a manifest, 19 sources in `data/raw/` (77 MB), statistics-office and framework parsers | Done |
| dbt: sources, staging of the 13 tables, `dim_departamento`, `dim_municipio`, `dim_periodo`, the supervisor's data in long form by block, total and splice tests | Done |
| Quarto site and CI (the site builds inside `make check`; it is not published separately, ADR-005) | Done |
| Governance documents: guide, logbook, 18 ADRs, licences | Done |
| Dictionary of the supervisor's 98 variables with each annualisation rule | Done |
| Inclusion facts (quarterly and annual, municipal and departmental), service points, activity, internet and education | Done |
| Annual panels: department 2018–2025 and municipality 2018–2024 | Done |
| Index by dimension with frozen, published weights, and its two sensitivity versions | Done |
| Interactive three-view atlas, inside the project page | Done |
| Econometrics: `src/iif/econ`, synthetic tests for the battery and for power, `metodologia/panel.qmd` with the results | Done |
| Power, equivalence and specification curve (ADR-018) | Done |
| Temporal-disaggregation annex, MIDAS, manuscript | Phase 4, pending |
| BigQuery: dbt target, load, partitioning, cost control and authorised views | Written; not yet run against a real project |
| Snowflake demonstration (same dbt models, stage, clone by vintage) | Later, no date |
| Thesis PDF | After deposit in the Javeriana institutional repository |
| Public page, the only one | <https://proyecto-davirson-git.vercel.app/en/research/fintech-inclusion> |

## How to cite

See [`CITATION.cff`](CITATION.cff). In text:

> Novoa Ramírez, D. (2026). *Inclusión financiera y crecimiento regional en Colombia: proyecto de investigación reproducible* [code and data]. <https://github.com/DavinsonR/financial-inclusion-colombia>

## Licence

- **Code** (`src/`, `dbt/`, `scripts/`, `tests/`, `notebooks/`): MIT, see [`LICENSE`](LICENSE).
- **Thesis text** (`paper/`): © 2026 Davirson Novoa Ramírez, all rights reserved until institutional deposit; afterwards, whatever licence that deposit sets.
- **Derived data** (`data/`, marts, `atlas/data/`): CC BY-SA 4.0, required by the licences of the financial supervisor, the ICT ministry and the education ministry. Attribution per source in [`docs/LICENCIAS_DATOS.md`](docs/LICENCIAS_DATOS.md) (ADR-012).
