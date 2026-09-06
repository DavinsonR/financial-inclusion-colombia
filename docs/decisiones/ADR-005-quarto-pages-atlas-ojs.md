# ADR-005 · Quarto + Vercel + atlas en Observable JS

- Fecha: 2026-09-06
- Estado: aceptada, con adenda

## Contexto

El autor quiere un sitio interactivo y útil para curiosos: un atlas del índice por región, dimensión y variable, la reproducción de la tesis, la bitácora y las decisiones. No hay presupuesto para servidores. Lo público no debe depender de Snowflake (ADR-014). El portafolio del autor ya enlaza a las siete anclas del README.

## Decisión

1. Sitio Quarto en la raíz del repo, `lang: es`, `freeze: auto`, kernel del `.venv`. Páginas: índice, reproducción de la tesis, fuentes (renderiza el manifiesto), diccionario legado, modelo de datos (diagrama mermaid de la estrella), crosswalk, metodología, anexo, atlas, bitácora y decisiones (incluyen los `.md` de `docs/`).
2. Despliegue en GitHub Pages con `actions/deploy-pages` desde `main`. URL prevista entonces: https://davinsonr.github.io/inclusion-financiera-colombia/ (sustituida por Vercel, ver adenda).
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

## Adenda 2026-09-06: Vercel en lugar de GitHub Pages

El autor ya despliega su portafolio en Vercel y no quiere una segunda plataforma. Vercel no puede correr Quarto ni Python en su build, así que el flujo es: CI renderiza `_site` en cada push a `main` y lo empuja, con un `vercel.json` mínimo, a la rama `site`; el proyecto de Vercel (`financial-inclusion-colombia`, enlazado al repositorio) despliega esa rama. En `main` hay un `vercel.json` con `ignoreCommand` que cancela cualquier build de Vercel sobre el código fuente. Único ajuste manual del autor, una sola vez: en Vercel, Settings → Git → Production Branch = `site`. Verificado el 2026-09-06: el proyecto existe, la rama `site` se despliega y las ramas de código quedan ignoradas. URL: https://financial-inclusion-colombia.vercel.app. La página de reproducción del trabajo de grado se retira del sitio: los resultados de la tesis no se publican (decisión del autor, misma fecha).

## Adenda 2026-09-06 (2): promover el primer despliegue a mano, y republicar a demanda

Cambiar la rama de producción en Vercel **no promueve los despliegues que ya existen**: solo hace de
producción los commits siguientes. Como `main` está deliberadamente ignorada, el dominio de producción se
quedó sin ningún despliegue asignado y respondía `DEPLOYMENT_NOT_FOUND`, que no es un fallo de compilación
sino "este dominio no apunta a nada". El arreglo es de diez segundos y del autor: Deployments → el
despliegue de la rama `site` → Promote to Production. A partir de ahí cada push de CI renueva producción.

De ahí salió un hueco real: CI solo publicaba con un push a `main`, así que no había forma de republicar el
sitio sin un commit de código. `ci.yml` acepta ahora `workflow_dispatch`; la condición de los pasos de
publicación (`github.ref == 'refs/heads/main'`) sigue valiendo porque el disparo manual se hace sobre `main`.

## Adenda 2026-09-06 (3): el atlas se dibuja sin CDN y con un solo tema

Quarto carga Observable Inputs desde jsDelivr: sin salida a internet los filtros y el mapa se caían (S-015).
d3 y topojson-client viven en `atlas/lib/` y los filtros son HTML plano. Y el atlas no lleva tokens de tema
oscuro: el sitio publica un único tema claro (`cosmo`), y unos tokens oscuros dejarían el mapa oscuro sobre
una página clara para quien tenga el sistema en oscuro. Cuando el sitio tenga tema oscuro, vuelven.

