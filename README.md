# Desarrollo Fintech e inclusión financiera como predictores del crecimiento económico regional en Colombia

**Evidencia de panel departamental con índice compuesto multidimensional (2017–2021)**

Trabajo de grado · Maestría en Economía · Pontificia Universidad Javeriana (Bogotá)
Autor: Davirson Novoa Ramírez · Director: Gabriel Penagos Londoño, Pontificia Universidad Javeriana

*English summary: see [Abstract](#abstract).*

<a id="status"></a>
## Estado

| Fecha | Hito |
|---|---|
| may-2026 | Proyecto de investigación enviado al director |
| jul-2026 | Concepto del jurado evaluador recibido |
| ago-2026 | Versión corregida radicada ante la Dirección de Posgrados, con las correcciones avaladas por el director |
| nov-2026 (previsto) | Grado |

El repositorio se publica por etapas. Hoy contiene la estructura, la documentación metodológica y la licencia. El código, los datos con su fuente y el PDF llegan después: ver [Qué hay y qué falta](#que-hay-y-que-falta).

## Resumen

Este trabajo pregunta si el desarrollo fintech y la inclusión financiera predicen el crecimiento económico regional en Colombia. Construye un índice compuesto multidimensional de inclusión financiera (IIF) por departamento mediante análisis de componentes principales y lo lleva a un panel departamental para el periodo 2017–2021, con el crecimiento del PIB real per cápita departamental como variable dependiente principal.

El hallazgo central se presenta sin maquillaje: bajo la especificación de referencia, efectos fijos de entidad y de tiempo, el coeficiente del índice **no es estadísticamente significativo** (β = −0,15; p = 0,984). En el modelo estático sin el rezago del crecimiento el coeficiente sí es significativo, con una magnitud cercana a la mitad. El trabajo documenta por qué la especificación exigente es la que manda, cuantifica el sesgo de Nickell del panel dinámico y explica por qué un GMM dinámico no ofrece una alternativa superior con esta dimensión temporal.

<a id="abstract"></a>
## Abstract

Does fintech development and financial inclusion predict regional economic growth in Colombia? This master's thesis builds a multidimensional composite index of financial inclusion (IIF) at the department level through principal component analysis and takes it to a department-level panel for 2017–2021, with the growth of real GDP per capita as the main dependent variable.

The headline result is reported as it is: under the reference specification, two-way fixed effects (entity and time), the index coefficient is **not statistically significant** (β = −0.15; p = 0.984). In the static model without the lagged growth term the coefficient is significant, at roughly half the magnitude. The thesis explains why the demanding specification is the one that rules, quantifies the Nickell bias of the dynamic panel, and shows why a dynamic GMM estimator is not a superior alternative at this time dimension.

## Pregunta de investigación

¿El desarrollo fintech y la inclusión financiera, medidos con un índice compuesto multidimensional, predicen el crecimiento económico de los departamentos colombianos?

Un rezago del índice ordena temporalmente la relación; **no** constituye una estrategia de identificación causal. El lenguaje del documento es de predicción, no de causalidad.

<a id="data"></a>
## Datos

| Elemento | Valor |
|---|---|
| Unidad | Departamento de Colombia |
| Periodo | 2017–2021 |
| Periodos por unidad (T) | 14 · frecuencia intra-anual, por confirmar en `data/raw/README.md` |
| Variable dependiente principal | Crecimiento del PIB real per cápita departamental |
| Robustez | PIB agregado departamental |
| Regresor de interés | IIF_Multidim, índice compuesto de inclusión financiera (4 componentes) |

Las fuentes primarias, su periodo, licencia y fecha de descarga se documentan en [`data/raw/README.md`](data/raw/README.md) cuando se suban los datos. Ninguna fuente se afirma aquí antes de estar en el repositorio.

<a id="method"></a>
## Método

1. **Índice compuesto (PCA).** IIF_Multidim se construye con análisis de componentes principales sobre las dimensiones de inclusión financiera. El índice principal conserva 4 componentes, que explican el 84,4 % de la varianza. Un índice basado solo en el primer componente queda como ejercicio de robustez secundario. El índice validado y el índice utilizado son el mismo.
2. **Especificación de referencia.** Panel con efectos fijos de entidad y de tiempo (two-way FE).
3. **Panel dinámico y sesgo de Nickell.** Con T = 14 y ρ̂ = 0,4279, el sesgo se cuantifica y se contrasta con el modelo estático sin el rezago del crecimiento. Se documenta por qué el GMM dinámico (Arellano-Bond / Blundell-Bond) no es superior en este panel.
4. **Errores estándar y dependencia transversal.** Prueba de Pesaran (CD) y errores estándar de Driscoll-Kraay.
5. **Submuestra prepandemia.** La estimación se repite excluyendo el periodo afectado por la pandemia.

Las decisiones de la versión corregida se explican en [`docs/decisiones-metodologicas.md`](docs/decisiones-metodologicas.md).

<a id="main-result"></a>
## Resultado principal

| Especificación | Coeficiente del IIF | Lectura |
|---|---|---|
| Efectos fijos de entidad y tiempo (referencia) | β = −0,15 · p = 0,984 | No significativo |
| Modelo estático sin rezago del crecimiento | Significativo · magnitud ≈ la mitad | Sensible a la especificación |

Un resultado que no sobrevive la especificación exigente se publica igual. Es el mismo criterio del proyecto [market-data-medallion](https://github.com/DavinsonR/market-data-medallion), donde solo el 11,8 % de las estrategias ganadoras dentro de muestra sobrevivió fuera de muestra: la validación existe para decir que no.

<a id="diagnostics"></a>
## Diagnósticos

| Diagnóstico | Valor / tratamiento |
|---|---|
| Sesgo de Nickell | Cuantificado con T = 14 y ρ̂ = 0,4279 |
| Dependencia transversal | Prueba de Pesaran (CD) |
| Errores estándar | Driscoll-Kraay |
| Pandemia | Submuestra prepandemia |
| Índice | 4 componentes, 84,4 % de varianza; PC1 solo como robustez |

## Estructura del repositorio

```
.
├── data/
│   ├── raw/          # datos fuente tal como se descargaron (con README de fuentes)
│   └── processed/    # panel limpio y el índice, listos para estimar
├── notebooks/        # PCA_GMM_Fintech_Tesis_v2.ipynb y sucesores
├── src/              # código reutilizable: construcción del índice, estimación, tablas
├── docs/             # decisiones metodológicas
├── paper/            # PDF del trabajo de grado (tras el depósito institucional)
├── CITATION.cff
├── LICENSE           # MIT para el código; ver "Licencia" para el texto y los datos
└── requirements.txt
```

<a id="que-hay-y-que-falta"></a>
## Qué hay y qué falta

| Pieza | Estado |
|---|---|
| Estructura, README, licencia, decisiones metodológicas | En el repositorio |
| Notebook (`PCA_GMM_Fintech_Tesis_v2.ipynb`) | Pendiente de subir por el autor |
| Datos crudos y procesados, con fuente y licencia | Pendiente de subir por el autor |
| PDF del trabajo de grado | Se publica tras el depósito en el repositorio institucional de la Javeriana |
| Página en el sitio del autor | <https://proyecto-davirson-git.vercel.app/es/research/fintech-inclusion> |

## Reproducir

Cuando el código y los datos estén en el repositorio:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
jupyter lab notebooks/
```

## Cómo citar

Ver [`CITATION.cff`](CITATION.cff). En texto:

> Novoa Ramírez, D. (2026). *Desarrollo Fintech e inclusión financiera como predictores del crecimiento económico regional en Colombia: evidencia de panel departamental con índice compuesto multidimensional (2017–2021)*. Trabajo de grado, Maestría en Economía, Pontificia Universidad Javeriana.

## Licencia

- **Código** (`src/`, `notebooks/`): MIT, ver [`LICENSE`](LICENSE).
- **Texto del trabajo de grado** (`paper/`): © 2026 Davirson Novoa Ramírez, todos los derechos reservados hasta el depósito institucional; después, la licencia que fije ese depósito.
- **Datos**: bajo los términos de cada fuente, documentados en `data/raw/README.md`.
