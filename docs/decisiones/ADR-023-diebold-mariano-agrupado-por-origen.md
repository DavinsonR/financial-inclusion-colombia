# ADR-023 · Diebold-Mariano agrupado por origen, y una puerta de calidad que no finge potencia

- Fecha: 2026-09-23
- Estado: aceptada (2026-09-23)
- Modifica: ADR-020, decisión 5 (la puerta de calidad) y la columna «p (DM pareado)» de su tabla

## Contexto

ADR-020 exige que ninguna especificación se publique sin ganarle al ingenuo «con prueba de
Diebold-Mariano pareada». `backtest.diebold_mariano` hace una prueba t sobre las 264 diferencias de
error absoluto (33 departamentos × 8 orígenes, 2018–2025) como si fueran independientes. No lo son: los
33 departamentos de un mismo origen comparten el choque del año. Un error del ingenuo en 2021 no es 33
fallos distintos, es el mismo rebote visto 33 veces.

La auditoría del 2026-09-23 (B-065) lo midió sobre el backtest real, con `backtest.rolling_origin` sobre
`frame.load_frame()` y las mismas especificaciones que publica el módulo:

| Medida | Combinación vs ingenuo |
|---|---|
| Ganancia en MAE, muestra completa | +38,6 % |
| p agrupado (264 pares, el que publica hoy `resultados.json`) | 2,0 × 10⁻⁷ |
| Correlación intraorigen de la diferencia de pérdidas | 0,60 |
| Efecto de diseño aproximado, 1 + (33 − 1) × 0,60 | ≈ 20 |
| p por origen (t sobre las 8 medias por origen, 7 g. l.) | **0,29** |
| Orígenes en que la combinación le gana al ingenuo | **3 de 8** (2021, 2022, 2023) |
| Ganancia en MAE sin el origen 2021 | +8,3 % (p por origen 0,44) |
| Régimen de calma (orígenes sin 2020 ni 2021): p agrupado → p por origen | 0,031 → 0,31 |

Diferencia media de error absoluto por origen, en puntos porcentuales (negativa = gana la combinación):

| 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|
| +0,33 | +0,03 | +0,59 | **−14,94** | −1,15 | −2,22 | +0,13 | +0,11 |

Con un efecto de diseño cercano a 20, los 264 pares aportan la información de unas trece observaciones
independientes, no la de 264. El «+34,6 %, p < 0,0001» de ADR-020 no es falso en el MAE, pero sí en el valor
p: la ventaja es real y está concentrada en un año, el de recuperación tras la ruptura, que es justo lo que
ADR-020 ya decía del mecanismo («la dummy no anticipa el choque: ayuda a recuperarse de él»). Lo que no
sostiene es la significancia.

El resto de especificaciones se comporta igual: todas pasan de p agrupados entre 10⁻⁷ y 10⁻⁵ a p por origen
entre 0,27 y 0,34, y ninguna le gana al ingenuo en más de 5 de los 8 orígenes.

Hay un segundo hecho que decide cómo se usa la prueba. Con 8 orígenes, el efecto mínimo detectable al 5 %
con potencia del 80 % es de **6,1 puntos** de MAE, cuando el MAE del ingenuo es 5,6. Es decir: la prueba por
origen no podría detectar ni una mejora del 100 %. Quitando 2021 el efecto detectable baja a 1,3 puntos
sobre un MAE de referencia de 3,8, alrededor de un tercio. La prueba correcta no tiene potencia para
funcionar como puerta de superioridad, y ninguna cantidad de cuidado estadístico cambia eso con ocho años.
Es la misma lección de S-017: una prueba se lee sabiendo su potencia.

## Decisión

1. **La inferencia sobre errores de pronóstico se agrupa por origen.** El estadístico de Diebold-Mariano
   se calcula sobre las medias por origen de la diferencia de pérdidas, con t de n − 1 grados de libertad
   (n = número de orígenes). El p agrupado sobre departamentos × orígenes deja de calcularse y de
   publicarse; no es una versión optimista de la prueba correcta, es una prueba de otra hipótesis.
2. **Junto al p se publican siempre tres números**: los orígenes ganados sobre el total (3 de 8), la
   ganancia en MAE y la ganancia sin el origen que más aporta (+8,3 % sin 2021). Ninguna cifra de ganancia
   del backtest aparece sola en el README, el atlas o la página de metodología.
3. **La puerta de calidad deja de ser una prueba de superioridad** y pasa a exigir, a la vez:
   - cobertura del backtest de al menos el 90 % (sin cambio respecto de ADR-020);
   - ganancia positiva en MAE sobre la ventana completa;
   - ganancia no negativa al quitar el origen que más aporta (prueba de «dejar fuera el mejor año»).

   El p por origen se publica como información, no como criterio. Con los datos de hoy la combinación
   pasa la puerta: +38,6 % completo y +8,3 % sin 2021.
4. **El texto publicado dice lo que la prueba permite decir**: que la combinación iguala o mejora al
   ingenuo en error medio, que la ventaja se concentra en la recuperación de 2021, y que con ocho años no
   es estadísticamente distinguible del ingenuo. La proyección se ofrece como escenario con incertidumbre
   (ADR-022), no como un modelo que haya demostrado superioridad.
5. **La regla vale para toda comparación de pronósticos sobre un panel** del proyecto, incluida
   `por_regimen`: la inferencia se agrupa en el nivel donde está la dependencia, y ese nivel es el año.

## Alternativas consideradas

- **Mantener el p agrupado.** Descartada: con un efecto de diseño cercano a 20 el error estándar está
  subestimado unas 4,5 veces (√20) y el valor p no significa lo que dice.
- **Errores HAC o Driscoll-Kraay sobre los 264 pares.** Con 8 periodos se reduce a la prueba por origen
  más la elección de un ancho de banda que no se puede calibrar con ocho puntos. Añade un parámetro sin
  añadir información.
- **Bootstrap salvaje agrupado por origen.** Con 8 grupos, la distribución de Rademacher solo tiene 256
  combinaciones distintas y el p queda discretizado. Es una sensibilidad razonable para más adelante, no
  la prueba de referencia.
- **Puerta estricta: publicar solo si el p por origen es menor que 0,05.** Es la lectura literal de
  ADR-020 y **la alternativa principal a esta propuesta**: hoy retiraría la capa de proyección del atlas.
  Se descarta porque, con un efecto detectable mayor que el propio MAE del ingenuo, la puerta no mediría
  calidad: sería una prohibición permanente vestida de prueba, que ningún modelo pasaría hasta que haya
  bastantes más años de datos. Si el autor prefiere no publicar proyecciones sin superioridad demostrada,
  esta es la opción coherente, y es legítima.
- **Exigir ganar en la mayoría de orígenes.** La combinación gana en 3 de 8 (prueba de signo, p = 0,73). La
  prueba de signo tiene todavía menos potencia que la t, y un criterio de mayoría castiga por igual perder
  por 0,03 puntos en 2019 que ganar por 14,9 en 2021.
- **Publicar el ingenuo en lugar de la combinación.** No se sigue de los datos: la combinación nunca pierde
  por más de 0,6 puntos en ningún origen y gana por mucho en el año de recuperación. La falta de
  significancia no es evidencia a favor del ingenuo.

## Consecuencias

- La columna «p (DM pareado)» de la tabla de ADR-020 queda invalidada; se anota como adenda allí y no se
  reescribe el registro.
- `backtest.diebold_mariano` y `evaluar` cambian: el p pasa a calcularse por origen, y `Veredicto` gana
  `origenes_ganados` y `ganancia_sin_mejor_origen`. El campo `dm_p` de `resultados.json` cambia de
  significado y de valor (de 0,0 a 0,29 para la combinación). Se regenera la salida.
- Prueba nueva en `tests/test_forecast.py`, en el estilo de S-017: un panel sintético con un choque común
  por año y sin ventaja real, donde el p agrupado rechaza y el p por origen no.
- La cifra de cabecera se debilita: «+38,6 %» pasa a leerse con «3 de 8 años» y «+8,3 % sin 2021». Es el
  precio de que la cifra sea verdadera.
- Deuda declarada: la capa de proyección no demuestra superioridad sobre el ingenuo. Cada año nuevo de
  datos añade un origen; la puerta se revisa cuando haya al menos 12 orígenes, o cuando el efecto
  detectable caiga por debajo de la ganancia medida.

## Cómo revertirla

La decisión 1 no se revierte: es una corrección, no una preferencia. La decisión 3 sí: pasar a la puerta
estricta es cambiar un criterio en `evaluar` (`p_por_origen < 0,05`) y aceptar que hoy la capa de
proyección no se publica.
