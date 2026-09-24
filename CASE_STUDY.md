# Case study: does financial inclusion predict regional growth in Colombia?

*[Leer en español](docs/CASO_DE_ESTUDIO.md)* · Davirson Novoa Ramírez · GitHub [@DavinsonR](https://github.com/DavinsonR) · [davirson.com](https://davirson.com)

## The problem

Financial inclusion is a policy goal in Colombia, and it is often defended with a regional correlation: departments with more banking grow faster. The trouble is that every department rides the same national cycle, so a regression that does not remove it can credit the index with what the whole economy did. The question of this MSc Economics thesis (Pontificia Universidad Javeriana, 2026) is narrower and harder: **once national trends are taken out, does financial inclusion still predict departmental growth, and how large an effect could the data have seen?**

## The data

19 public sources — the financial supervisor (SFC), the statistics office (DANE), the ICT and education ministries and the 2024 national geostatistical framework — downloaded by `iif acquire` with a sha256, row count and source date for each file in `data/raw/manifest.jsonl`. Every series is resolved to DIVIPOLA codes and loaded into a dbt star schema on DuckDB. The outputs are annual panels for 33 departments (2018–2025) and 1,123 municipalities (2018–2024). The grain is annual by design: no annual value is ever repeated across four quarters ([ADR-001](docs/decisiones/ADR-001-frecuencia-anual.md)).

## Four decisions that shaped the answer

1. **The denominator ([ADR-017](docs/decisiones/ADR-017-denominador-del-indice.md)).** Five of the index's eight variables are amounts divided by GDP, and GDP growth is the dependent variable. Dividing by contemporaneous GDP makes the index rise by arithmetic whenever the economy falls: a correlation manufactured by construction. A placebo with frozen numerators proved it, and the index now divides by the **lagged** product.
2. **Measure the assumption before picking the method ([ADR-015](docs/decisiones/ADR-015-seleccion-de-variables-del-indice.md)).** PCA needs variables that share common variance. The Kaiser-Meyer-Olkin statistic for the "use" and "depth" dimensions came out below 0.5, so there is no PCA: variables are standardised and weighted equally within each dimension, the weights are frozen on a calibration window, and the implicit weight of every variable is published.
3. **A null needs its power ([ADR-018](docs/decisiones/ADR-018-potencia-y-equivalencia.md)).** A non-significant coefficient does not distinguish "no effect" from "this design would not see one". The project publishes the minimum detectable effect and an equivalence test (TOST) next to the coefficient, and explains why the design has the power it has: two-way fixed effects remove most of the index's variance.
4. **Honest forecast evaluation ([ADR-023](docs/decisiones/ADR-023-diebold-mariano-agrupado-por-origen.md)).** The 2026–2028 forecast layer is compared with a naive forecast using a Diebold-Mariano test grouped by forecast origin, not pooled over departments × origins, which would test a different hypothesis and overstate the evidence. The forecast is offered as a scenario with uncertainty, not as a model with proven superiority.

## The result

**A bound, not an absence.** With department and year fixed effects the index does not predict growth, and the design states which effect sizes it rules out and which it cannot speak to. The contrast with the naive regression is the lesson: without time effects the coefficient is +0.027 and strongly significant; with them it vanishes. Across the specification curve, 50 of 80 specifications are significant without time effects and 5 of 80 with them. The only design with a signal (an initial-exposure design on the 2018 index) is taken apart by the project itself: initial urbanisation explains it just as well, and it does not survive a Holm correction. With wild-cluster-bootstrap inference the design rules out effects above about 0.55 pp of annual growth per identifying standard deviation of the index, and cannot rule out ±0.5 pp. Exact figures, standard errors and tests: [README, Main result](README.md#main-result).

## Stack

Python 3.11 with `uv` · dbt on DuckDB (BigQuery target written, Snowflake as a later demonstration) · pandas, linearmodels, statsmodels, scipy, factor-analyzer · Quarto with Observable JS, d3 and TopoJSON for the atlas · GitHub Actions with pinned actions and locked dependencies · pytest and dbt tests that re-derive every published figure.

## What it demonstrates

- End-to-end ownership: from raw public files to a warehouse, an index, a map and a defensible econometric statement.
- Judgement over output: measuring assumptions before choosing methods, publishing the power of a null, and dismantling the one signal found.
- Traceability: 23 decision records written before the code, a root-cause logbook, and CI that fails if a published number drifts from the code.
- Governed use of AI coding agents: hard rules, ADRs and adversarial audits, with the author directing and answering for every module ([How this was built](README.md#how-this-was-built)).

## Links

- Repository overview: [README.md](README.md) · Spanish: [README.es.md](README.es.md)
- Project page and interactive atlas: <https://davirson.com/en/research/fintech-inclusion>
- Decisions: [`docs/decisiones/`](docs/decisiones/README.md) · Methodology: [`metodologia/`](metodologia/panel.qmd)
- How to cite: [`CITATION.cff`](CITATION.cff)
