# ADR-011 · uv + Quarto por tarball, sin R

- Fecha: 2026-09-06
- Estado: aceptada

## Contexto

El README anterior proponía `python -m venv` y `pip install -r requirements.txt`. El proyecto ahora tiene un paquete (`src/iif`), un CLI, dbt con dos adaptadores, pandera, linearmodels y Quarto. En la sesión del asistente la API de GitHub está bloqueada y no hay `apt` ni `gh`; los tarballs de Releases sí descargan (S-006). Parte de la literatura de desagregación temporal y de econometría espacial vive en R.

## Decisión

1. Solo `uv`: `pyproject.toml` con hatchling, `uv.lock` versionado, grupos `dev`, extras `geo` y `site`. Nunca `pip install` (R-02). `requirements.txt` se exporta desde uv para lectores que no lo usan.
2. Quarto se instala con `scripts/install_quarto.sh` desde el tarball de Releases, versión fijada (1.7.32), en `~/.local/opt`. En CI, `quarto-actions/setup`.
3. PDF con tectonic, también por tarball, sin TeX Live.
4. Sin R. Lo que exista solo en R (por ejemplo `tempdisagg`, `splm`) se reimplementa en Python o se documenta como límite. Un solo runtime es más fácil de reproducir y de mantener en CI.
5. Python 3.11 o superior.

## Alternativas consideradas

- conda o mamba: más pesado; resuelve R pero añade un gestor más.
- pip con `requirements.txt`: sin resolución reproducible y sin lock.
- Quarto por `apt` o `gh release download`: no disponibles en la sesión.
- Quarto con R y `renv`: dos runtimes y dos locks.

## Consecuencias

- `make setup` es un comando y funciona igual en local y en CI (caché por `uv.lock`).
- El paquete debe existir antes de `uv sync` o reinstalarse (B-022).
- Si un método solo existe en R, se anota en la bitácora y se decide caso por caso.

## Cómo revertirla

Añadir R exige un ADR nuevo, `renv.lock`, un paso en `ci.yml` y en `install_quarto.sh`, y decidir qué parte del sitio lo usa.
