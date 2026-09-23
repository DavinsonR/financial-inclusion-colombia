# ADR-019 · Grano anual y horizonte de tres años para el pronóstico departamental

- Fecha: 2026-09-23
- Estado: aceptada

## Contexto

El proyecto va a publicar una capa de pronóstico del crecimiento departamental sobre el atlas. Antes del
código hay que fijar dos cosas que no se pueden cambiar después sin rehacerlo todo: a qué frecuencia se
pronostica y hasta dónde.

**La frecuencia ya está decidida y no se reabre.** ADR-001 fijó el grano anual porque las Cuentas
Nacionales Departamentales del DANE solo existen con periodicidad anual, y R-05 prohíbe repetir un valor
anual en cuatro trimestres. El error que eso produce está documentado: la versión de la tesis de 2026 lo
cometió y le costó el capítulo de rezagos, porque `crec_pib(t) == crec_pib(t−1)` en el 64,3 % de las
observaciones y el rezago del regresor caía dentro del mismo año calendario. La capa de pronóstico hereda
esa decisión sin discusión.

**El horizonte sí hay que decidirlo, y la materia prima es escasa.** `pib_departamento_anual.parquet` tiene
33 departamentos × 21 años (2005–2025), 693 filas sin un solo nulo. En log-diferencias eso son **20
observaciones de crecimiento por departamento**. Con esa cantidad, un ARIMA converge a su deriva en pocos
pasos y deja de aportar información sobre una extrapolación lineal.

Medición sobre el panel, con origen móvil y ARIMA(1,1,0) con atípicos declarados (ADR-020) frente a la
deriva de la media histórica, 132 pares por horizonte:

| Horizonte | MAE ARIMA | MAE deriva | Ventaja del ARIMA |
|---|---|---|---|
| 1 año | 4,927 | 5,772 | **+14,6 %** |
| 2 años | 6,207 | 8,120 | **+23,6 %** |
| 3 años | 7,846 | 9,049 | **+13,3 %** |
| 4 años | 7,337 | 7,746 | +5,3 % |
| 5 años | 8,740 | 8,610 | **−1,5 %** |

A cuatro años la ventaja es marginal y a cinco el modelo ya pierde contra la deriva. *(Advertencia: los
orígenes disponibles para medir a cinco años son solo cuatro por departamento y todos tienen el COVID
dentro de la ventana de pronóstico, así que los niveles absolutos están inflados. Lo que la tabla sostiene
es el perfil relativo, no las cifras.)*

Dos hechos más del panel condicionan el diseño:

- **La población ya está proyectada hasta 2050** (`poblacion_departamento_anual.parquet`, 33 departamentos).
  El denominador per cápita se conoce de antemano: solo hay que pronosticar el PIB y dividir.
- **2024 es `provisional` y 2025 es `preliminar`.** El DANE los va a revisar.

## Decisión

1. **El pronóstico es anual y cubre 2026, 2027 y 2028.** Tres años es donde el modelo todavía aporta sobre
   una extrapolación lineal. Publicar 2029 o 2030 sería publicar la deriva con un intervalo más ancho y un
   nombre más sofisticado.
2. **Se pronostica el PIB real y el per cápita sale por división** con las proyecciones de población del
   DANE, que son un dato y no un pronóstico propio. No se modela el per cápita directamente.
3. **Cada corrida guarda su vintage** —qué versión de los datos usó y qué `estado_dato` tenía cada año— en
   la salida, desde la primera. Sin eso, la revisión de 2024 y 2025 contamina retroactivamente cualquier
   histórico de desempeño y el backtest deja de valer dentro de un año.
4. **Se acepta el anclaje al consenso nacional**, con la reconciliación jerárquica que detallará ADR-021.
   Aquí solo se registra que la decisión de alcance está tomada y que la arquitectura es abajo-arriba
   anclada, no abajo-arriba pura. Lo que la habilita es que la jerarquía cierra **en la ventana que
   importa**: desde 2013 la suma de los 33 departamentos difiere del total nacional del DANE en menos
   del 0,08 % (máximo 0,072 % en 2025). En los años retropolados 2005–2012 la aditividad no es exacta
   y llega a **1,28 % en 2009**; eso contamina el entrenamiento en su tramo más antiguo, no la
   restricción sobre la que se reconcilia. Véase ADR-021.
5. **El IIF no entra como regresor del pronóstico.** ADR-016 establece que el índice no predice
   el crecimiento, y la cota del nulo se publica en la rama `auditoria-potencia-y-denominador`
   (ADR-018, pendiente de fusión). Usarlo aquí contradiría el resultado del propio repositorio. En el
   atlas las dos capas conviven y se ve que no coinciden, que es la ilustración visual del nulo.

## Alternativas consideradas

- **Horizonte de cinco años, hasta 2030.** Da una narrativa más redonda para el sitio y la tabla de arriba
  dice que a cinco años el modelo ya no le gana a una línea recta. Se descarta: el mapa comunicaría
  precisión que no existe.
- **Un solo año, 2026.** Es lo más defendible en términos estrictos de error, y deja una capa sin
  contenido: un mapa de un año no muestra trayectoria y no justifica la infraestructura.
- **Pronosticar directamente el crecimiento per cápita.** Ahorra un paso y desperdicia información: las
  proyecciones de población del DANE son conocidas hasta 2050 y meterlas dentro del modelo las trataría
  como ruido en vez de como dato.
- **Trimestralizar con el ITAED.** ADR-001 ya lo dejó pendiente y aquí seguiría chocando con R-05: el ITAED
  cubre 13 departamentos más Bogotá, no los 33. Sirve como insumo de nowcast del año en curso (ADR-021),
  no como grano del pronóstico.

## Consecuencias

- El módulo de pronóstico produce tres años por departamento, no una senda abierta. La estructura de
  `atlas.yaml` y del JSON de series se dimensiona para eso.
- Aparece una obligación operativa nueva: **registrar la vintage en cada corrida**. Es la parte que se
  olvida y la que hace inútil el histórico si falta.
- Al fijar el horizonte en tres años, el proyecto renuncia a competir con las sendas a diez años del MFMP.
  Es deliberado: aquellas son nacionales y tienen supuestos fiscales detrás; esta es departamental y solo
  tiene 20 observaciones por unidad.
- La decisión 5 cierra la puerta a la pregunta que el proyecto va a recibir más veces —"¿y por qué no usas
  tu índice para pronosticar?"— con una respuesta que ya está publicada y medida.

## Cómo revertirla

El horizonte es un parámetro del módulo de pronóstico y de `config/atlas.yaml`. Ampliarlo es cambiar un
número y volver a correr; lo que no se puede revertir sin rehacer la pieza es la promesa publicada en el
sitio, así que el cambio pasa por una adenda a este ADR y no por una edición silenciosa.
