# ADR-015 · Selección, normalización y ponderación de las variables del índice

- Fecha: 2026-09-06
- Estado: aceptada, con adenda del mismo día tras medir

## Contexto

El diccionario tiene 98 variables de la Superintendencia. 27 son totales de bloque presentes en las dos
tablas, que es el conjunto candidato para un índice continuo de 2018 a 2025. Tres mediciones sobre el panel
construido deciden el diseño:

1. **Las variables crudas miden población.** La correlación entre cada variable y la población
   departamental va de 0,58 a 0,94 (pagos 0,94; cuentas de ahorro 0,92; transacciones 0,91). Un índice
   sobre variables sin normalizar tendría como primer componente el tamaño del departamento, no la
   inclusión financiera.
2. **El total de transacciones es exactamente la suma de sus componentes** (razón mediana 1,0000).
   Incluir el total y sus partes contaría lo mismo dos veces y daría peso artificial a esa dimensión.
3. **La cobertura no es uniforme.** El crédito de consumo de bajo monto solo está en el 79,5 % de las filas
   departamentales y en el 59,5 % de las municipales; el resto de candidatas supera el 98 % y el 89 %.

## Decisión

1. **Normalización antes de cualquier cálculo.** Los conteos pasan a **por cada 10.000 habitantes**
   (población total del DANE) y los montos a **porcentaje del PIB** en el panel departamental y del valor
   agregado en el municipal. Los montos como razón sobre producto son la definición estándar de
   profundidad financiera y, al ser dos series nominales, no necesitan deflactor. Tras normalizar, la
   correlación con la población baja a un rango de −0,28 a 0,69: lo que queda es relación económica, no
   aritmética.
2. **Ocho variables, una por concepto**, sin anidamiento:
   - *Acceso* (1): corresponsales físicos activos por 10.000 habitantes.
   - *Uso* (4): número y monto de transacciones en corresponsales; número y saldo de cuentas de ahorro.
   - *Profundidad* (3): monto de crédito de consumo, de vivienda y microcrédito, como porcentaje del producto.
3. **Exclusiones, cada una con su motivo**: el crédito de bajo monto por cobertura insuficiente; los
   componentes de las transacciones por estar contenidos en su total; los cortes por género y por rango de
   SMMLV porque son desagregaciones del mismo total; las cuentas de ahorro electrónicas porque solo existen
   hasta 2021 y los corresponsales móviles porque solo existen desde 2021, y cualquiera de las dos rompería
   la continuidad de la serie.
4. **Dos etapas.** Una combinación por dimensión sobre las variables estandarizadas da tres subíndices; el
   compuesto es el promedio de los tres, con las tres dimensiones pesando igual. El método de combinación
   dentro de cada dimensión se decidió midiendo, ver la adenda.
   Que las dimensiones pesen igual es una decisión, no un resultado: evita que la dimensión con más
   variables domine el compuesto.
5. **La dimensión de acceso tiene una sola variable y su subíndice es esa variable estandarizada.** No se
   simula un componente principal donde no hay estructura que descomponer, ni se añaden variables anidadas
   (propios, tercerizados, contratados) para aparentar una dimensión más rica de lo que la fuente permite.
6. **Pesos congelados.** Media, desviación y cargas se estiman en la ventana de calibración 2018-2019 y se
   guardan en `config/index.yaml`. Los años siguientes se transforman con esos parámetros: el índice puede
   crecer por encima de su rango inicial, que es justo lo que debe hacer si la inclusión aumenta.
   Recalibrar es una decisión explícita que cambia el archivo, no un efecto secundario de añadir un año.
7. **Los pesos implícitos por variable se publican siempre**, en la escala original y en la estandarizada.
   Un peso implícito negativo en una variable que debería sumar es una señal de alarma, no un detalle
   técnico, y tiene que estar a la vista.
8. **Dos alternativas como sensibilidad**: pesos iguales dentro de cada dimensión y el índice de distancia
   de Sarma. Se publica la correlación de rangos entre las tres versiones; ninguna se esconde.

## Alternativas consideradas

- Un solo componente principal sobre las nueve variables juntas: no da subíndices por dimensión, que es
  justo lo que el proyecto necesita para el atlas y para responder al jurado.
- Normalizar por adultos en vez de por habitantes: el DANE publica población por edad, pero no de forma
  consistente para todo el periodo municipal; se prefiere una sola definición para los dos niveles.
- Escalado min-max: comprime el índice a [0, 1] dentro de cada año y borra la evolución en el tiempo,
  además de ser sensible al valor extremo que define el máximo.
- Recalibrar los pesos cada año: el índice dejaría de ser comparable entre años, que es la comparación que
  el proyecto quiere hacer.

## Consecuencias

- El índice mide intensidad relativa por habitante y por producto, no tamaño.
- Con ocho variables y tres dimensiones, la de acceso queda documentada como la más pobre: la fuente no
  ofrece más medidas de acceso continuas en todo el periodo. Los puntos de atención de la
  Superintendencia (oficinas, cajeros, datáfonos) empiezan en 2023 y entrarán como extensión cuando el
  panel corto tenga sentido.
- Cambiar la selección exige editar `config/index.yaml` y volver a congelar: queda registrado en git.

## Cómo revertirla

Editar `config/index.yaml` (lista de variables, denominadores y ventana) y volver a correr
`iif index build`. Las pruebas que fijan la reproducibilidad con pesos congelados avisan del cambio.

## Adenda 2026-09-06: el componente principal no lo sostienen los datos

El punto 4 preveía un componente principal por dimensión. Al estimarlo sobre la ventana de calibración
aparecieron tres señales, todas medidas, no supuestas:

| Dimensión | KMO | Varianza del primer componente | Peso implícito con signo contrario |
|---|---|---|---|
| Uso (4 variables) | 0,314 | 41,9 % | monto de transacciones, −0,035 |
| Profundidad (3 variables) | 0,404 | 55,0 % | microcrédito, −0,009 |

Un KMO por debajo de 0,5 significa que las variables no comparten suficiente varianza común: el primer
componente no resume un factor, sino que reparte ruido. Forzarlo produce exactamente el defecto que la
auditoría del trabajo de grado había encontrado en su índice: una variable que debería sumar entra
restando. Repetirlo a sabiendas sería indefendible.

**Decisión revisada**: dentro de cada dimensión las variables pesan igual (1/k sobre las estandarizadas).
No exige estructura factorial, no puede dar peso negativo a una variable que debe sumar, y es el método que
recomienda la literatura de índices compuestos cuando el análisis factorial no se sostiene. El componente
principal se conserva **como sensibilidad**, con su KMO publicado al lado, para que se vea por qué no es el
método principal. La correlación de rangos entre las dos versiones es 0,96: la elección casi no cambia el
orden de los departamentos, y por eso conviene quedarse con la que no tiene pesos negativos.

Lección para el proyecto: un KMO por debajo de 0,5 descarta el PCA; se mide antes de elegir el método, no
después de publicarlo.
