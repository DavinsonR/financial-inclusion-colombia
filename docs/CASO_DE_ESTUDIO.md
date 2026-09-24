# Caso de estudio: ¿la inclusión financiera predice el crecimiento regional en Colombia?

*[Read in English](../CASE_STUDY.md)* · Davirson Novoa Ramírez · GitHub [@DavinsonR](https://github.com/DavinsonR) · [davirson.com](https://davirson.com)

## El problema

La inclusión financiera es una meta de política en Colombia y a menudo se defiende con una correlación regional: los departamentos con más servicios financieros crecen más. El problema es que todos los departamentos se mueven con el mismo ciclo nacional, y una regresión que no lo descuenta le atribuye al índice lo que hizo la economía entera. La pregunta de esta tesis de Maestría en Economía (Pontificia Universidad Javeriana, 2026) es más estrecha y más difícil: **una vez descontadas las tendencias nacionales, ¿la inclusión financiera sigue prediciendo el crecimiento departamental, y qué tan grande tendría que ser un efecto para que los datos lo vieran?**

## Los datos

19 fuentes públicas —la Superintendencia Financiera (SFC), el DANE, los ministerios TIC y de Educación y el Marco Geoestadístico Nacional 2024— descargadas por `iif acquire` con sha256, número de filas y fecha de la fuente de cada archivo en `data/raw/manifest.jsonl`. Cada serie se resuelve a códigos DIVIPOLA y se carga en un esquema en estrella de dbt sobre DuckDB. El resultado son paneles anuales de 33 departamentos (2018–2025) y 1.123 municipios (2018–2024). El grano es anual por diseño: ningún valor anual se repite en cuatro trimestres ([ADR-001](decisiones/ADR-001-frecuencia-anual.md)).

## Cuatro decisiones que dieron forma a la respuesta

1. **El denominador ([ADR-017](decisiones/ADR-017-denominador-del-indice.md)).** Cinco de las ocho variables del índice son montos divididos por el PIB, y el crecimiento del PIB es la variable dependiente. Dividir por el PIB contemporáneo hace que el índice suba por aritmética cada vez que la economía cae: una correlación fabricada por la construcción. Un placebo con numeradores congelados lo demostró, y el índice ahora divide por el producto **rezagado**.
2. **Medir el supuesto antes de escoger el método ([ADR-015](decisiones/ADR-015-seleccion-de-variables-del-indice.md)).** El PCA necesita variables que compartan varianza común. El estadístico de Kaiser-Meyer-Olkin de las dimensiones de uso y profundidad salió por debajo de 0,5, así que no hay PCA: las variables se estandarizan y pesan igual dentro de cada dimensión, los pesos se congelan en una ventana de calibración y el peso implícito de cada variable se publica.
3. **Un nulo necesita su potencia ([ADR-018](decisiones/ADR-018-potencia-y-equivalencia.md)).** Un coeficiente no significativo no distingue entre "no hay efecto" y "este diseño no lo vería". El proyecto publica el efecto mínimo detectable y una prueba de equivalencia (TOST) junto al coeficiente, y explica por qué el diseño tiene la potencia que tiene: los efectos fijos de dos vías eliminan la mayor parte de la varianza del índice.
4. **Evaluación honesta del pronóstico ([ADR-023](decisiones/ADR-023-diebold-mariano-agrupado-por-origen.md)).** La capa de proyección 2026–2028 se compara con un pronóstico ingenuo mediante una prueba de Diebold-Mariano agrupada por origen del pronóstico, no apilada sobre departamentos × orígenes, que probaría otra hipótesis y exageraría la evidencia. La proyección se ofrece como escenario con incertidumbre, no como un modelo con superioridad demostrada.

## El resultado

**Una cota, no una ausencia.** Con efectos fijos de departamento y año el índice no predice el crecimiento, y el diseño dice qué tamaños de efecto descarta y sobre cuáles no puede pronunciarse. El contraste con la regresión ingenua es la lección: sin efectos de tiempo el coeficiente es +0,027 y muy significativo; con ellos desaparece. En la curva de especificación, 50 de 80 especificaciones salen significativas sin efectos de tiempo y 5 de 80 con ellos. El único diseño con señal (un diseño de exposición inicial con el índice de 2018) lo desmonta el propio proyecto: la urbanización inicial lo explica igual de bien y no sobrevive a la corrección de Holm. Con inferencia por bootstrap salvaje agrupado, el diseño descarta efectos mayores que unos 0,55 pp de crecimiento anual por desviación identificante del índice, y no puede descartar ±0,5 pp. Cifras exactas, errores estándar y pruebas: [README, Resultado principal](../README.es.md#main-result).

## Stack

Python 3.11 con `uv` · dbt sobre DuckDB (objetivo BigQuery escrito, Snowflake como demostración posterior) · pandas, linearmodels, statsmodels, scipy, factor-analyzer · Quarto con Observable JS, d3 y TopoJSON para el atlas · GitHub Actions con acciones fijadas y dependencias bloqueadas · pytest y pruebas de dbt que rederivan cada cifra publicada.

## Qué demuestra

- Responsabilidad de punta a punta: de los archivos públicos crudos a un warehouse, un índice, un mapa y una afirmación econométrica defendible.
- Criterio por encima del producto: medir supuestos antes de escoger métodos, publicar la potencia de un nulo y desmontar la única señal encontrada.
- Trazabilidad: 23 registros de decisión escritos antes del código, una bitácora de causa raíz y una CI que falla si una cifra publicada se separa del código.
- Uso gobernado de agentes de IA para programación: reglas duras, ADR y auditorías adversariales, con el autor dirigiendo y respondiendo por cada módulo ([Cómo se construyó](../README.es.md#cómo-se-construyó)).

## Enlaces

- Visión general del repositorio: [README.es.md](../README.es.md) · inglés: [README.md](../README.md)
- Página del proyecto y atlas interactivo: <https://davirson.com/es/research/fintech-inclusion>
- Decisiones: [`decisiones/`](decisiones/README.md) · Metodología: [`metodologia/`](../metodologia/panel.qmd)
- Cómo citar: [`CITATION.cff`](../CITATION.cff)
