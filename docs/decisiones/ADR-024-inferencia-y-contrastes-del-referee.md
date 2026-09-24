# ADR-024 · Inferencia con el error agrupado, tendencias previas y los contrastes que pidió el referee

- Fecha: 2026-09-23
- Estado: aceptada (2026-09-23)
- Modifica: ADR-016 (puntos 1, 4 y 6) y ADR-018 (grados de libertad del TOST y del MDE)

## Contexto

El informe de referee de identificación del 2026-09-23 (recomendaciones A1 a A10) revisó la batería de
`src/iif/econ/` sobre la corrida publicada del 2026-09-17. No discute el nulo. Discute cómo está acotado.
Las cifras de partida, todas de `data/processed/econ/resultados.json` en esa corrida:

| Medida | Valor publicado | Problema señalado |
|---|---|---|
| β base (efectos de entidad y tiempo) | +0,00382, SE agrupado 0,00618, p = 0,54, N = 228, G = 33 | ninguno en sí |
| Bootstrap salvaje por clúster | p = 0,481 (Rademacher, 999 réplicas) | studentiza con el error **homocedástico** `sqrt(e'e/gl · (X'X)⁻¹)`, no con el CRVE: no es el WCR de Cameron, Gelbach y Miller |
| TOST a ±0,25 / ±0,50 pp por DE identificante | p = 0,280 / 0,038 | usa gl = 186 (residuales); con errores agrupados la referencia es t(G − 1) = t(32) |
| MDE al 80 % | 0,58 pp por DE identificante; 2,14 pp por DE bruta | factor normal (2,80), no t(32) |
| IC 95 % | [−0,28, +0,54] pp por DE identificante | normal; no hay intervalo por inversión del bootstrap |
| Driscoll-Kraay | SE 0,00343, la mitad del agrupado | con T = 7 no es creíble y se publica como fila de igual rango |
| Estudio de eventos | 2022: +0,0141 (SE 0,0050); 2025: +0,0071 (SE 0,0035) | "no puede contrastar tendencias previas" por construcción, aunque `fct_actividad_departamento_anual` tiene el PIB constante 2005–2025 |
| Control de convergencia | `log_pib_rezago` = −0,332 con efectos de entidad y T = 7 | sesgo de Nickell que puede contaminar β |
| Dependiente | PIB total, con las secciones B (minería) y K (financieras) | K sube con el crédito por construcción; B mueve Arauca, Casanare, Meta, La Guajira y Cesar |
| Denominador | placebo de solo-denominador −0,2525 (p = 0,0007) con el PIB contemporáneo, citado en ADR-017 | la cifra no está en el JSON (R-09); el fijo (+0,0053, p = 0,34) no se publica al lado |
| Cuadrático | p = 0,042 agrupado, 0,099 bootstrap | no aparece en `panel.qmd` ni se ajusta por comparaciones múltiples |
| Curva de especificación | pp de "solo entidad" escalados con la DE de dos vías | la DE correcta es la que queda tras los efectos de entidad |

Además, el texto de `panel.qmd` describe en la sección 6 un placebo "dentro de cada año" y muestra el p del
placebo por trayectoria (B-074), y la sección 4 llama "shift-share" a un diseño que multiplica una sola
participación por una sola serie común, sin muchos choques (BHJ) ni pesos de Rotemberg (GPSS).

El autor aprobó aplicar todas las recomendaciones del grupo A con este ADR.

## Decisión

1. **Inferencia (A5).** El bootstrap salvaje por clúster se studentiza con el error agrupado (CRVE, CR1:
   factor G/(G − 1) · (N − 1)/(N − K)) y la nula impuesta, sobre el diseño completo con los efectos fijos
   como variables ficticias, de modo que los residuos de cada réplica son los del modelo completo y no los
   del espacio ya desmediado. Se publica con pesos de Rademacher y con los seis puntos de Webb (2014). El
   intervalo del 95 % se obtiene por inversión del bootstrap (el conjunto de β₀ que la prueba con la nula
   β = β₀ no rechaza), y el TOST gana una versión bootstrap: dos contrastes unilaterales con la nula
   impuesta en −m y en +m. El TOST y el MDE analíticos pasan a t(G − 1) = t(32) grados de libertad; los
   186 residuales se conservan en el JSON solo como referencia. Driscoll-Kraay se sigue calculando y pasa
   a una nota: deja de ser fila de `principales`.
2. **Tendencias previas (A2).** Estudio de eventos con dependiente de crecimiento del PIB real total desde
   2006 (`fct_actividad_departamento_anual.pib_constante_2015_mm`, 2005–2025), exposición fija (índice de
   2018 estandarizado), año de referencia 2019 y efectos de entidad y año. Se publica la prueba F conjunta
   de los trece coeficientes previos (2006–2018) con el CRVE y F(q, G − 1), y su p por bootstrap salvaje
   del estadístico de Wald con la nula impuesta. Se repite con urbanización de 2018 × año como control, y
   con el PIB real per cápita (población implícita del DANE: PIB corriente / PIB per cápita corriente, que
   coincide con la proyección de población desde 2018).
3. **Base sin Nickell (A3).** Dos filas nuevas en `principales`: una con las condiciones iniciales × año
   (log del PIB per cápita de 2018 × año y urbanización de 2018 × año) en lugar de `log_pib_rezago`, y
   otra sin controles. La especificación base publicada **no cambia de definición**.
4. **Dependiente limpia (A4).** Crecimiento del valor agregado a precios constantes per cápita sin las
   secciones B y K, construido en `frame.load_frame` con una consulta de solo lectura a
   `staging.stg_dane__va_departamento_actividad_anual`. Fila de robustez, con las variantes sin B y sin K
   por separado. Advertencia: el volumen encadenado no es aditivo; la suma de secciones a precios
   constantes es una aproximación que se mide contra el valor agregado total del DANE y se publica.
5. **Causalidad inversa (A6).** Adelanto: crecimiento_t sobre índice_{t+1}. Granger inverso: Δíndice_t
   sobre crecimiento_{t−1}. Los dos con efectos de entidad y año y errores agrupados.
6. **Denominador en el JSON (A7).** El placebo de solo-denominador (todos los numeradores congelados en su
   valor de 2018, de modo que el índice solo se mueve por sus denominadores) se estima con el producto
   contemporáneo, rezagado y fijo, con y sin 2020–2021, y el β del índice real con cada denominador. El del
   denominador fijo, recalibrado, entra en `principales` como fila coprincipal.
7. **Quién identifica (A8).** Pesos de Aronow y Samii (2016) por departamento: la participación de cada uno
   en Σ x̃², con x̃ el regresor residualizado contra los efectos fijos y los controles. Al lado, la
   participación en la población de 2018 y la estimación ponderada por población.
8. **Familia de contrastes (A9).** Tabla de Holm sobre la base, las tres dimensiones, la exposición
   inicial, los seis años posteriores del estudio de eventos y el cuadrático (doce contrastes), con p de
   t(G − 1). Romano-Wolf no se implementa: exige re-estimar los doce modelos con los mismos pesos en cada
   réplica y, con Holm ya válido bajo cualquier dependencia, no cambiaría la lectura. El cuadrático se
   publica en `panel.qmd`.
9. **Unidades naturales (A10).** El β de acceso se traduce a puntos porcentuales por cada 10 corresponsales
   activos por 10.000 habitantes, con la desviación congelada de `config/index.yaml` (R-15). En
   `curve.py`, los pp de "solo entidad" se escalan con la DE que queda tras los efectos de entidad y los
   controles, no con la de dos vías.
10. **Nombres (O5).** El "shift-share" pasa a llamarse **diseño de exposición inicial** en los textos y en
    las claves nuevas del JSON (`exposicion_inicial_contraste`). La clave vieja no la lee nadie fuera de
    `panel.qmd`, así que se renombra en lugar de duplicarse. La función `designs.shift_share` se conserva
    como alias de `designs.exposicion_por_adopcion`.
11. **Convergencia (economista 2, A9).** Sigma-convergencia (DE del log del PIB real per cápita por año,
    2005–2025) y beta-convergencia incondicional de corte transversal (33 observaciones, crecimiento medio
    anual 2005–2025 sobre el log del nivel de 2005), leídas del JSON.
12. **Textos (A1).** La sección 6 de `panel.qmd` describe el placebo que se muestra (trayectoria); la cota
    se escribe "por DE identificante (≈ X pp por DE bruta)" con X medido; lo que el código no hace
    (SAR/SDM) no se promete: el código estima SLX.

## Alternativas consideradas

- **Solo cambiar gl = 186 por gl = 32 y dejar el bootstrap como estaba.** Barato y corrige la mitad del
  problema. Se descarta: el bootstrap homocedástico no tiene el refinamiento asintótico que justifica
  usarlo con pocos clústeres, y es la pieza que el texto presenta como la corrección.
- **Pesos de Webb como únicos.** Webb se recomienda sobre todo con menos de doce clústeres; con 33, las 2³³
  combinaciones de Rademacher bastan. Se publican los dos y el texto dice si discrepan.
- **Reemplazar `log_pib_rezago` en la base.** Sería cambiar la especificación después de ver resultados,
  que es justo lo que el referee reprocha de B-074. Las condiciones iniciales entran como filas nuevas.
- **Tendencias previas con el índice anterior a 2018.** No existe: la SFC empieza en 2018. No hace falta:
  la exposición es fija en 2018 y lo que se contrasta es si los más expuestos ya crecían distinto antes.
- **Romano-Wolf.** Ver punto 8.

## Consecuencias

- `resultados.json` cambia de forma: `principales` pierde Driscoll-Kraay (va a `notas`) y gana el
  denominador fijo, las condiciones iniciales × año y la fila sin controles; cada fila lleva una `clave`.
  Aparecen los bloques `tendencias_previas`, `dependiente_sin_bk`, `causalidad_inversa`, `denominador`,
  `aronow_samii`, `familia_holm`, `unidades_naturales` y `convergencia`, y
  `shift_share_contraste` se renombra a `exposicion_inicial_contraste`.
- Las cifras de ADR-018 dejan de ser las vigentes (ver su adenda). Si una corrección cambia la conclusión,
  se publica así: ver "Resultado medido".
- `tests/test_resultados_publicados.py` sigue comparando el JSON entero contra una corrida nueva y fija
  además las cifras de este ADR que el texto cita.

## Resultado medido

Corrida del 2026-09-23 sobre el mismo almacén que la del 2026-09-17 (β base idéntico, +0,00382). Todas las
cifras están en `resultados.json` y las que se citan aquí, fijadas en `tests/test_resultados_publicados.py`.

**Una corrección cambia la conclusión, y se publica así.** El titular del proyecto ("el diseño descarta
efectos mayores que medio punto por desviación típica") ya no se sostiene con la inferencia que este ADR
declara de referencia:

| Medida | Antes (gl = 186, bootstrap homocedástico) | Después |
|---|---|---|
| p bootstrap de β | 0,481 | 0,550 (Rademacher, CRVE); 0,539 (Webb) |
| TOST ±0,25 pp por DE identificante | p = 0,280 | t(32): 0,282 · bootstrap: 0,293 |
| TOST ±0,50 pp | p = 0,038, **descartado** | t(32): 0,042, descartado por poco · bootstrap: **0,068, no descartado** (Webb 0,072) |
| TOST ±1,00 pp | p < 0,001 | t(32) y bootstrap: ≤ 0,001, descartado |
| Margen más pequeño que el TOST descarta | — | t(32): 0,48 pp · bootstrap: **0,55 pp** (≈ 2,0 pp por DE bruta); Webb 0,53 |
| MDE al 80 % | 0,58 pp (2,14 por DE bruta) | 0,60 pp (2,21 por DE bruta) |
| IC 95 % en pp por DE identificante | [−0,28, +0,54] | t(32): [−0,30, +0,55] · bootstrap invertido: [−0,28, +0,61] |

La redacción correcta de la cota pasa a ser: el diseño descarta efectos mayores que unos 0,55 pp de
crecimiento anual por desviación típica identificante del índice (≈ 2 pp por desviación bruta) y no puede
descartar ±0,50 pp.

El resto de las correcciones **no** cambia el veredicto:

- Filas nuevas de `principales`: denominador fijo +0,0053 (p bootstrap 0,35); condiciones iniciales × año
  en lugar del rezago del ingreso +0,0005 (0,93); sin controles +0,0029 (0,61). El sesgo de Nickell del
  control no estaba sosteniendo el nulo.
- Dependiente sin B ni K: +0,0031 (p bootstrap 0,33); sin B, +0,0029; sin K, +0,0029. La suma de secciones
  en volumen se separa del total en una mediana de 0,28 % (máximo 8,4 %) desde 2018.
- Tendencias previas (2006–2018, 13 coeficientes, 32 departamentos con exposición): p bootstrap 0,41 con
  el PIB total y 0,25 con el per cápita; 0,67 y 0,53 con la urbanización de 2018 × año. El F analítico
  contra F(13, 31) rechaza en tres de las cuatro filas (p de 0,003 a 0,026, y 0,15 en la del PIB total):
  con 13 restricciones y 32 clústeres el Wald agrupado sobre-rechaza, y la referencia es el bootstrap. Se
  publican las dos.
- Adelanto: −0,0054 (p bootstrap 0,42). Granger inverso: −1,55 (p bootstrap 0,040) con el índice
  publicado, pero −0,86 (0,27) con el de denominador fijo: con el denominador rezagado, Δíndice_t contiene
  mecánicamente el crecimiento de t − 1 con signo negativo.
- Placebo de solo-denominador, con los controles de la base: −0,228 (p = 0,0007) contemporáneo; −0,129
  (p = 0,030) rezagado; +0,129 (p = 0,44) fijo. **El denominador rezagado reduce el sesgo pero no lo
  elimina** (el referee lo anticipó en O7); sin controles el rezagado da +0,058 (p = 0,28). Es la razón
  del denominador fijo como fila coprincipal.
- Aronow-Samii: los cinco departamentos que más pesan (Arauca, San Andrés, Caquetá, Amazonas, Antioquia)
  aportan el 47 % de la identificación con el 15 % de la población; el panel equivale a 15 departamentos
  con peso igual. Ponderado por población, β = +0,0062 (p = 0,19).
- Holm sobre doce contrastes: cuatro tienen p < 0,05 sin ajustar (exposición inicial, eventos 2022 y 2025,
  cuadrático) y ninguno sobrevive (el menor ajustado, 0,093). El cuadrático pasa a p bootstrap 0,13.
- Acceso en unidades naturales: +0,14 pp por cada 10 corresponsales activos por 10.000 habitantes
  (IC 95 % [−0,41, +0,69]).
- Convergencia: la DE del log del PIB real per cápita sube de 0,464 (2005) a 0,521 (2025); la beta
  incondicional de corte transversal es −0,0023 (p = 0,72). No hay convergencia incondicional.
- Curva de especificación: con la escala correcta, la mediana de "solo entidad" pasa de 0,40 a 0,95 pp por
  DE; los recuentos (49 de 80 y 5 de 80 significativas) no cambian.

## Cómo revertirla

Cada pieza es una función o un bloque de `run.py`: quitar el bloque del diccionario de salida y su
sección de `panel.qmd`. Volver al bootstrap homocedástico es `robustness.wild_cluster_bootstrap` de la
versión anterior (git), y volver a gl = 186 es pasar `gl` en lugar de `clusteres − 1` a `power.tost` y
`power.mde`.
