# ADR-025 · La alternativa de Sarma es una distancia tipo Sarma: faltante sigue faltante y techo congelado

- Fecha: 2026-09-23
- Estado: aceptada
- Modifica: ADR-004 (decisión 8) y ADR-015 (punto de la sensibilidad), en lo que toca a la alternativa «Sarma»
- Cierra: B-064

## Contexto

ADR-004 y ADR-015 publican, junto al compuesto, dos versiones alternativas del índice: el primer
componente principal por dimensión y un «índice de distancia de Sarma». La segunda entra también en la
batería econométrica como sensibilidad del resultado principal (ADR-016).

La auditoría del 2026-09-23 (B-064) y el informe de lectura macroeconómica (informe 02, punto 1.5)
encontraron tres cosas en `src/iif/index/build.py::_sarma`:

1. **Rellenaba faltantes con cero.** `fillna(0.0)` ponía una variable no observada a la máxima distancia
   del ideal. Cuatro filas reales sin alguna variable (Guainía 2019; Vaupés 2018, 2019 y 2025) entraban
   a la sensibilidad con un valor inventado: 264 filas con valor frente a 260 con compuesto. Choca con
   R-13 y con ADR-008.
2. **El techo no estaba congelado.** Cada variable se dividía por su máximo en **todo el panel**, no en la
   ventana de calibración. Añadir un año con un máximo nuevo cambiaba el valor de todos los años ya
   publicados, justo lo que ADR-004 prohíbe para el compuesto.
3. **No es el índice de Sarma (2008).** Las z se recortan en 0, así que el suelo es la media de la
   calibración y no un mínimo; la distancia se toma sobre las ocho variables con el mismo peso, no por
   dimensión. Llamarlo «índice de Sarma» atribuía a la autora una construcción que no es la suya.

## Decisión

1. **Se rotula «distancia tipo Sarma»** en código, en `metodologia/indice.qmd` y en toda cifra nueva. La
   columna sigue llamándose `iif_sarma` (y `iif_sensibilidad_sarma` en el mart), porque renombrarla
   rompería el contrato de dbt y del atlas sin ganar nada; el rótulo humano es el que cambia.
2. **Un faltante sigue faltante.** La fila a la que le falta alguna de las ocho variables no tiene
   distancia tipo Sarma, igual que no tiene compuesto (R-13).
3. **El techo se congela en la ventana de calibración** (2018-2019), como las medias y las desviaciones:
   es el máximo de las z recortadas en 0 dentro de la ventana. Lo que lo supera cuenta como haber llegado
   al ideal (se recorta a 1). El nivel municipal usa el techo del departamental, igual que usa sus medias
   y desviaciones, para que las dos escalas sean comparables.
4. **El recorte en 0 se conserva y se documenta.** Es lo que hace de esto una distancia al ideal desde la
   media y no desde un mínimo normativo, que ADR-004 descartó por exigir umbrales por variable.
5. La alternativa sigue siendo **sensibilidad**, no método.

## Medición

Con los datos del 2026-09-23 (`data/processed/indice_*`, `uv run iif index`):

| Medida | Antes | Después |
|---|---|---|
| Filas departamentales con valor | 264 | 260 (= filas con compuesto) |
| Spearman agrupado con el compuesto | 0,899 | 0,859 |
| Spearman agrupado con el componente principal | 0,849 | 0,815 |
| Spearman con el compuesto dentro de cada año, media (mínimo) | — | 0,797 (0,594 en 2023) |
| Spearman con el compuesto en cambios anuales | — | 0,447 |

El techo congelado **satura**: los corresponsales superan el techo de 2018-2019 en 101 de 264 filas, el
número de transacciones en 65 y su monto en 30. Es el coste de la comparabilidad en el tiempo. Una
distancia que satura a partir de 2021 en la variable que más crece ordena peor los cambios, y eso es lo
que dice la correlación de 0,447 en cambios: la distancia tipo Sarma no es una sensibilidad fuerte del
resultado sobre la dinámica, y así se publica.

El efecto sobre el coeficiente de la sensibilidad econométrica lo recalcula `uv run iif econ`; B-064
estimaba que corregir solo los faltantes lo llevaba de −0,105 (p 0,336) a −0,108 (p 0,326). La cifra
vigente es la de `data/processed/econ/resultados.json`, no esta.

## Alternativas consideradas

- **Techo del panel completo (lo que había).** Da una distancia sin saturación, pero cada año nuevo
  reescribe los anteriores. Se descarta por la misma razón por la que se congelan las medias.
- **Techo normativo por variable** (por ejemplo, el percentil 95 de un panel internacional). Es lo que
  hace Sarma y lo que ADR-004 descartó: exige elegir un umbral por variable sin una fuente que lo
  respalde para los departamentos colombianos.
- **Sin recorte en 0 (distancia a un mínimo observado).** Es más fiel a Sarma y cambia la lectura: un
  departamento muy por debajo de la media se distinguiría de otro apenas por debajo. Queda como extensión
  para el índice v2; aquí no se reabre la construcción, solo se corrige lo que violaba reglas del repo.
- **Imputar los faltantes.** Inventaría el dato que R-13 prohíbe inventar.
- **Retirar la alternativa.** ADR-015 se comprometió a publicarla y a no esconder ninguna versión. Se
  conserva, con su rótulo y sus límites.

## Consecuencias

- `indice_departamento_anual.parquet` y `indice_municipio_anual.parquet` cambian en `iif_sarma`; el
  mart, la sensibilidad econométrica y la curva que la usan cambian al regenerar (`dbt build`,
  `iif econ`, `iif curva`).
- `src/iif/econ/run.py` y `src/iif/econ/curve.py` rotulan todavía la sensibilidad como «Sarma» e «índice
  de Sarma»; deben pasar a «distancia tipo Sarma» en el mismo cierre.
- Las pruebas `test_sarma_deja_faltante_lo_que_falta` y `test_sarma_congela_el_techo_en_la_calibracion`
  de `tests/test_index.py` fijan las dos propiedades.

## Cómo revertirla

Devolver `_sarma` a su versión anterior (máximo de todo el panel y `fillna(0.0)`) restituye las cifras
de antes; hacerlo exige una adenda aquí que explique por qué R-13 no aplica, y no se ve cuál.
