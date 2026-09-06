# ADR-005 · Quarto + GitHub Pages + atlas en Observable JS

- Fecha: 2026-09-06
- Estado: aceptada

## Contexto

El autor quiere un sitio interactivo y útil para curiosos: un atlas del índice por región, dimensión y variable, la reproducción de la tesis, la bitácora y las decisiones. No hay presupuesto para servidores. Lo público no debe depender de Snowflake (ADR-014). El portafolio del autor ya enlaza a las siete anclas del README.

## Decisión

1. Sitio Quarto en la raíz del repo, `lang: es`, `freeze: auto`, kernel del `.venv`. Páginas: índice, reproducción de la tesis, fuentes (renderiza el manifiesto), diccionario legado, modelo de datos (diagrama mermaid de la estrella), crosswalk, metodología, anexo, atlas, bitácora y decisiones (incluyen los `.md` de `docs/`).
2. Despliegue en GitHub Pages con `actions/deploy-pages` desde `main`. URL prevista: https://davinsonr.github.io/inclusion-financiera-colombia/.
3. Atlas en Observable JS dentro de Quarto, sin servidor. Contrato de datos en `config/atlas.yaml`: `atlas_meta.json`, `geo_*.json` en TopoJSON simplificado desde el MGN 2024, series columnares por nivel y frecuencia. Presupuesto total < 3 MB.
4. Las páginas de fases futuras existen desde ahora como `draft: true` para que el sitio compile.

## Alternativas consideradas

- Streamlit o Dash: exigen servidor y un proceso de Python vivo; no encajan en Pages.
- Power BI publicado: tablero opcional en PBIP conectado a Snowflake para demostrar la conexión, pero no como vía pública principal (licencia y dependencia de Snowflake).
- Sitio estático a mano (HTML y D3): más trabajo y sin integración con el manuscrito.

## Consecuencias

- Todo lo que muestra el sitio sale de Parquet exportados por `iif export` (fase 2) y se versiona en `atlas/data/`.
- `quarto render` es parte de `make check`; una página rota rompe CI.
- El renombrado del repo cambia la URL del sitio; el portafolio se actualiza después.

## Cómo revertirla

El atlas depende solo de los archivos de `atlas/data/`. Cualquier otro front (React, Svelte, Power BI) puede leer el mismo contrato. Cambiar el generador del sitio exige rehacer las páginas `.qmd`, no los datos.
