# ADR-020 · 2020 y 2021 entran al modelo como atípicos declarados

- Fecha: 2026-09-23
- Estado: aceptada

## Contexto

El PIB real de Colombia cayó 7,46 % en 2020 y rebotó 10,26 % en 2021 (log-diferencias del agregado
nacional). En el panel departamental la dispersión de 2020 es de otro orden que la de cualquier otro año:
desviación típica de 5,23 puntos entre departamentos, con el percentil 10 en −14,29 %. Para comparar, la
desviación típica de 2023 es 1,01 y la de 2024, 1,02.

Un ARIMA estimado sobre una serie que contiene esa caída y ese rebote **aprende un ciclo que no existe**.
Con 20 observaciones anuales por departamento, dos de ellas extremas y consecutivas en direcciones
opuestas, el componente autorregresivo captura la oscilación y la proyecta hacia adelante.

La medición, con origen móvil sobre los 33 departamentos (entrena hasta el año anterior, pronostica el
siguiente, avanza el origen; 264 pares por modelo, orígenes 2018–2025):

| Modelo | MAE | vs ingenuo | p (DM pareado) |
|---|---|---|---|
| ARIMA(1,1,0) + atípicos | **3,633** | +34,6 % | < 0,0001 |
| ARIMA(1,1,1) + atípicos | 3,806 | +31,5 % | < 0,0001 |
| ARIMA(0,1,0) deriva | 3,974 | +28,4 % | < 0,0001 |
| ARIMA(1,1,0) sin atípicos | 4,473 | +19,5 % | < 0,0001 |
| Ingenuo (último crecimiento) | 5,555 | referencia | — |

Declarar los atípicos vale **15 puntos porcentuales de mejora relativa** frente a la misma especificación
sin declararlos (+34,6 % contra +19,5 %).

Pero el promedio esconde el mecanismo, y el mecanismo es lo que decide cómo se implementa. Partiendo la
ventana por origen:

| Origen | Mejor modelo | MAE | vs ingenuo | Qué pasa |
|---|---|---|---|---|
| **2020** | *ninguno le gana al ingenuo* | — | de −3,7 % a −7,5 % | 2020 no está en el entrenamiento: la columna de la dummy es toda ceros y su coeficiente no se identifica. `+atípicos` y la versión sin ellos dan **exactamente el mismo número** (11,343). |
| **2021** | ARIMA(1,1,0) + atípicos | 4,961 | **+72,5 %** | Ya se vio 2020. La dummy lo absorbe y el modelo no extrapola la caída. |
| **2022–2025** | ARIMA(0,1,0) deriva | 2,177 | +28,3 % (p = 0,002) | En calma, la deriva simple le gana a todas las variantes con atípicos. |

**La dummy no anticipa el choque: ayuda a recuperarse de él.** Esa es toda su función, y conviene decirlo
antes de que alguien lea el +34,6 % como capacidad predictiva.

Un aviso adicional que viene de fuera: el laboratorio `macro-forecast-lab-latam` encontró que este tipo de
resultado es frágil a la frecuencia de los datos. Sobre Colombia, el mismo periodo de ruptura da
conclusiones opuestas —ambas significativas al 5 %— según se use el ISE mensual del DANE o el PIB
trimestral del FMI. Nada de lo que sigue se presenta como una ley general.

## Decisión

1. **2020 y 2021 entran como dos variables exógenas binarias**, una por año, en todas las especificaciones
   ARIMA del pronóstico departamental. Se declaran; no se imputan, no se interpolan y no se recortan de la
   muestra.
2. **No se usa un detector automático de atípicos.** Los dos años están fijados por nombre en el código.
   Un detector con 20 observaciones marcaría también años que son ciclo y no ruptura, y su umbral sería un
   hiperparámetro más que ajustar mirando el error.
3. **El pronóstico publicado es una combinación, no una especificación única.** La tabla por origen muestra
   que ninguna variante domina en todos los regímenes: con atípicos gana tras la ruptura, la deriva simple
   gana en calma, y en el año del choque no gana nadie. Promediar es más estable que elegir el ganador de
   un backtest con 8 orígenes.
4. **El texto publicado junto al mapa dice explícitamente que las dummies no anticipan choques.** La
   comparación del origen 2020 —donde declarar los atípicos no cambia ni un decimal— se publica como
   evidencia, no se omite por incómoda.
5. **Ninguna especificación se publica si no le gana al ingenuo en el backtest**, con prueba de
   Diebold-Mariano pareada y no solo con diferencia de MAE. Es la puerta de calidad del módulo, equivalente
   a lo que `qa_deposito.py` hacía para el documento.

## Alternativas consideradas

- **Excluir 2020 y 2021 de la muestra.** Rompe la serie en dos tramos de 15 y 4 observaciones, y con 20
  puntos no sobra ninguno. Además borra información real: la profundidad de la caída departamental es
  precisamente lo que distingue a Bogotá de Vichada en ese año.
- **Interpolar 2020 y 2021 como si no hubieran ocurrido.** Fabrica datos, y R-05 y el historial del
  proyecto están para impedir exactamente eso.
- **Un modelo de cambio de régimen (Markov switching).** Es la respuesta teóricamente correcta y necesita
  muchas más observaciones de las que hay: con 20 puntos anuales y un solo episodio de ruptura, las
  probabilidades de transición no se identifican.
- **Una sola dummy 2020–2021 en vez de dos.** Ahorra un parámetro y trata como iguales una caída de −7,5 %
  y un rebote de +10,3 %. Se descarta porque el signo opuesto es justamente lo que confunde al componente
  autorregresivo.
- **Recortar el efecto con un estimador robusto en vez de dummies.** Es defendible y menos transparente:
  una dummy con nombre de año se lee en la tabla de coeficientes; una función de pérdida robusta no.

## Consecuencias

- Todas las corridas del módulo llevan las dos columnas exógenas, también las de los modelos de referencia
  que las ignoran, para que la matriz de comparación sea la misma.
- Al proyectar 2026–2028 las dummies valen cero, así que **no afectan al pronóstico publicado por sí
  mismas**: su efecto es indirecto, vía unos parámetros autorregresivos estimados sin la contaminación de
  la ruptura. Conviene tenerlo presente al explicar el modelo.
- Queda una deuda declarada: si aparece otra ruptura, este ADR no la cubre y habrá que decidir de nuevo.
  El diseño reacciona a choques pasados, no a futuros.
- La decisión 3 obliga a que el módulo produzca varias especificaciones y las combine, lo que encarece el
  código respecto de ajustar un solo ARIMA. Es el precio de que ninguna variante domine.

## Cómo revertirla

Las dummies son un argumento `exog` del ajuste. Quitarlas es un cambio de una línea y devuelve la
especificación sin declarar atípicos, cuyo desempeño está medido arriba (+19,5 % en vez de +34,6 %). La
decisión 3 —combinar en vez de elegir— es independiente y se revierte por separado.

## Adenda 1 (2026-09-23): los valores p de la tabla no son válidos

La columna «p (DM pareado)» trata los 264 pares como independientes, y los 33 departamentos de un mismo
origen comparten el choque (correlación intraorigen 0,60). Agrupada por origen, la combinación pasa de
p = 2,0 × 10⁻⁷ a p = 0,29 y le gana al ingenuo en 3 de 8 orígenes. Las ganancias en MAE de la tabla siguen
siendo correctas. La corrección de la prueba y la nueva puerta de calidad están en ADR-023; B-065 en la
bitácora.
