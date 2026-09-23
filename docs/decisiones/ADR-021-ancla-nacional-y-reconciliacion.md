# ADR-021 · Ancla nacional y reconciliación proporcional, no MinT

- Fecha: 2026-09-23
- Estado: aceptada

## Contexto

ADR-019 aceptó anclar el pronóstico departamental al consenso nacional y dejó la mecánica para aquí. Hay
dos cosas que decidir: si el anclaje paga, y cómo se reparte el ajuste entre los 33 departamentos.

**Por qué hace falta un ancla.** Un pronóstico abajo-arriba puro —33 ARIMA independientes, sumados— no
tiene por qué cuadrar con nada. Medido sobre los orígenes 2018–2025, la suma de los 33 se desvía del total
nacional real en un 2,91 % en media absoluta, pero la distribución está muy sesgada:

| Origen | Desajuste de la suma contra el total real |
|---|---|
| 2018 | +0,58 % |
| 2019 | +0,43 % |
| **2020** | **+11,75 %** |
| 2021 | +4,77 % |
| 2022 | +1,48 % |
| 2023 | +2,88 % |
| 2024 | +1,14 % |
| 2025 | +0,22 % |

En los años tranquilos el abajo-arriba cuadra casi solo. En 2020 se pasó de largo por casi doce puntos:
33 modelos extrapolando cada uno su propia tendencia no vieron la caída, y sus errores no se cancelaron
sino que se sumaron en la misma dirección. Ahí es donde un ancla vale algo.

**Nada de esto tendría sentido si la jerarquía no cerrara**, y aquí hay un matiz que conviene no
esconder. Cierra desde 2013, y no antes:

| Tramo | Brecha de la suma contra el total nacional |
|---|---|
| 2005–2012 (retropolados) | de +0,23 % a **+1,28 %**, máximo en 2009 |
| 2013–2017 | ≤ 0,06 % |
| **2018–2025 (ventana de backtest)** | **≤ 0,072 %**, máximo en 2025 |

La no aditividad de 2005–2012 viene de la retropolación del DANE a base 2015, que no impone suma exacta
en los años reconstruidos. Afecta al tramo más antiguo del entrenamiento, no a la restricción sobre la
que se reconcilia: en la ventana donde se mide y donde se va a pronosticar, la agregación es exacta a
menos de una décima de punto porcentual.

## Decisión

### 1. El ajuste se reparte proporcional al tamaño, no por MinT

La hoja de ruta proponía reconciliación MinT (*minimum trace*), que reparte el desajuste en proporción a la
varianza de pronóstico de cada serie. Se midieron las dos contra el abajo-arriba, sobre los mismos ocho
orígenes, con ancla perfecta:

| Método | MAE (% del nivel) | vs abajo-arriba |
|---|---|---|
| Abajo-arriba, sin ancla | 3,803 | referencia |
| **Reparto proporcional al tamaño** | **2,235** | **+41,2 %** |
| Reconciliación MinT diagonal | 2,994 | +21,3 % |

**El método más simple gana, y por el doble.** La razón es que MinT con pesos diagonales asigna el ajuste
según la varianza en niveles, que escala con el cuadrado del tamaño y termina cargando el ajuste sobre los
departamentos grandes más de lo que le corresponde. El desajuste agregado, en cambio, se distribuye entre
todos más o menos en proporción a su peso. Se adopta el reparto proporcional y se registra la medición
para que nadie vuelva a proponer MinT sin repetirla.

### 2. El anclaje paga mientras el consenso no se equivoque por más de tres puntos y medio

El ancla no es perfecta: importa el error de pronóstico de un tercero. Degradando el ancla con ruido
lognormal y promediando 400 sorteos por nivel:

| Error del ancla | MAE | vs abajo-arriba |
|---|---|---|
| 0,0 pp (perfecta) | 2,235 | +41,2 % |
| 1,0 pp | 2,450 | +35,6 % |
| 2,0 pp | 2,954 | +22,3 % |
| 3,0 pp | 3,452 | +9,2 % |
| **4,0 pp** | 4,099 | **−7,8 %** |
| 6,0 pp | 5,537 | −45,6 % |

**El punto de equilibrio está en torno a 3,5 puntos porcentuales.** Por debajo de eso, anclar mejora el
pronóstico departamental; por encima, lo empeora. Un consenso de analistas para Colombia a un año suele
moverse dentro de 1 a 1,5 puntos en años normales, que es cómodamente territorio de ganancia.

### 3. Se declara la trampa: donde más paga el ancla es donde el ancla falla

La ganancia por origen, con ancla perfecta y reparto proporcional:

| Origen | Abajo-arriba | Reconciliado | Ganancia |
|---|---|---|---|
| **2020** | 12,17 % | 3,51 % | **+71,2 %** |
| 2023 | 2,60 % | 1,38 % | +47,1 % |
| 2021 | 5,21 % | 3,49 % | +32,9 % |
| 2024 | 1,43 % | 1,12 % | +22,0 % |
| 2018 | 1,89 % | 1,64 % | +13,6 % |
| 2025 | 1,07 % | 0,99 % | +7,6 % |
| 2019 | 1,52 % | 1,43 % | +6,2 % |
| 2022 | 4,53 % | 4,33 % | +4,4 % |

El +71,2 % de 2020 es **con un ancla que acierta**. En 2020 real ningún consenso acertó: los analistas
proyectaban crecimiento positivo y la economía cayó 7,46 %, un error muy por encima de los 3,5 puntos del
punto de equilibrio. Es decir: **el año en que el anclaje más habría ayudado es el año en que el ancla
habría fallado con nosotros.** La ganancia realista se parece más al +4 % a +22 % de los años tranquilos
que al +71 % del cuadro.

Esto no invalida la decisión —anclar sigue pagando en la mayoría de los estados del mundo— pero prohíbe
venderlo como un seguro contra crisis, que es exactamente lo contrario de lo que es.

### 4. Fuentes del ancla, y se publica cuál y de cuándo

Por orden de preferencia: **Banrep, Encuesta mensual de expectativas de analistas económicos (EME)**, que
además publica la dispersión entre analistas; **MinHacienda, Marco Fiscal de Mediano Plazo**, que da senda
a varios años; y **FMI, WEO**, que tiene API y sirve de contraste. La pieza publicada nombra el ancla y su
fecha de corte. Un mapa anclado sin decir a qué está anclado es un mapa que atribuye a su autor la visión
de otro.

### 5. Se publica también la versión sin anclar

Las dos capas viajan al navegador. Quien mire el mapa debe poder ver cuánto del resultado viene de los
datos departamentales y cuánto del consenso nacional. Sin esa comparación, el anclaje es una caja negra.

### 6. Los escenarios salen de la dispersión de la EME, no de la imaginación

Central, optimista y pesimista se construyen con el consenso y con el mínimo y el máximo de los analistas
encuestados. Son tres anclas y una sola metodología, con fuente citable, en vez de tres supuestos
inventados.

### 7. El año en curso se nowcastea aparte

El PIB departamental sale con cerca de doce meses de rezago. Para el año corriente: **ITAED trimestral**
para los 13 departamentos más Bogotá que cubre, y **shift-share sectorial** sobre el valor agregado por
actividad para los otros 20. El ITAED no entra como grano del pronóstico —R-05 y ADR-001 lo impiden— sino
como insumo del nivel de partida.

## Alternativas consideradas

- **Abajo-arriba puro, sin ancla.** Es el más honesto en el sentido de que no importa el error de nadie, y
  es peor: 3,803 contra 2,235 de MAE. El desajuste de 2020 muestra que los errores de 33 modelos
  independientes no se cancelan cuando el choque es común.
- **Arriba-abajo puro**, repartiendo el total nacional según participaciones históricas. Descarta toda la
  información departamental y convierte el mapa en una representación de la estructura del PIB, no de su
  dinámica.
- **MinT completo con matriz de covarianzas estimada** (*shrinkage*), en vez de la versión diagonal. Con 20
  observaciones por departamento y 33 series, la covarianza 33×33 no se estima con decencia; y la versión
  diagonal ya pierde contra el reparto proporcional, así que la promesa de la versión completa tendría que
  ser grande para justificar el riesgo.
- **Anclar a la senda del MFMP en vez de a la EME.** El MFMP es oficial y anual, y está construido con
  supuestos fiscales que no son un pronóstico central sino una planeación. La EME se actualiza cada mes y
  trae dispersión, que es lo que hace falta para los escenarios.

## Consecuencias

- El módulo de pronóstico produce dos juegos de cifras por escenario: sin anclar y reconciliado. El
  contrato del atlas tiene que acomodar los dos.
- Aparece una dependencia externa con calendario propio: la EME se publica mensualmente y el mapa queda
  fechado respecto de ella. Hay que decidir cada cuánto se refresca; mientras no se decida, la fecha del
  ancla es parte de la pieza.
- La decisión 1 contradice la hoja de ruta original, que proponía MinT. La hoja de ruta queda superada en
  ese punto y este ADR es la referencia.
- El punto de equilibrio de 3,5 puntos es una cifra que conviene revisar cuando haya histórico propio de
  error del consenso; hoy se toma de la degradación simulada, no de la serie real de la EME, que no está
  en el repositorio.

## Cómo revertirla

El anclaje es un paso posterior al pronóstico base: quitarlo devuelve el abajo-arriba puro, cuyo desempeño
está medido arriba. Cambiar el reparto proporcional por MinT es cambiar el vector de pesos; ambos quedan
implementados para que la comparación se pueda repetir.
