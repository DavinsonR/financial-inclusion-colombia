# ADR-022 · La incertidumbre viaja al mapa como capa propia, no como heurística

- Fecha: 2026-09-23
- Estado: aceptada

## Contexto

El atlas ya publica el índice de inclusión financiera con la infraestructura de ADR-005: `config/atlas.yaml`
declara qué indicadores viajan, `iif atlas` los emite como matrices año × unidad, y el sitio los consume
desde `public/atlas/*.json`. Añadir la capa de proyección es extender ese contrato, no construir uno nuevo.

El problema no es técnico. **Un mapa de calor de un pronóstico puntual, sin su intervalo, comunica una
precisión que el modelo no tiene.** Un color intenso sobre Vaupés porque el valor central dice 3,1 % se lee
igual que un color intenso sobre Bogotá, y no significan lo mismo.

Se midió el ancho del intervalo al 80 % para 2026–2028, por departamento:

| Departamento | Peso en el PIB | Ancho 2026 | Ancho 2028 |
|---|---|---|---|
| Amazonas | 0,07 % | **2,5 pp** | 6,5 pp |
| Bogotá D.C. | 26,70 % | 3,3 pp | 8,2 pp |
| Valle del Cauca | 9,97 % | 4,2 pp | 11,7 pp |
| *mediana* | *1,52 %* | *6,2 pp* | *13,7 pp* |
| Arauca | 0,49 % | 11,4 pp | 23,7 pp |
| Chocó | 0,38 % | 14,3 pp | 35,9 pp |
| Meta | 3,20 % | 14,7 pp | **42,5 pp** |
| Putumayo | 0,35 % | **17,5 pp** | 41,0 pp |

Tres cosas de esta tabla deciden el diseño:

1. **El ancho varía siete veces entre el departamento más preciso y el menos preciso** a un año: de 2,5 pp
   en Amazonas a 17,5 pp en Putumayo.
2. **El tamaño no sirve como sustituto de la confianza.** La correlación de Spearman entre el peso en el
   PIB y el ancho del intervalo es **−0,358**: débil y no monótona. Meta tiene el 3,20 % del PIB y uno de
   los intervalos más anchos del país, porque su serie depende del petróleo; Amazonas tiene el 0,07 % y el
   intervalo más estrecho de los 33. Un mapa que apagara los departamentos pequeños "porque son
   inciertos" se equivocaría en los dos casos.
3. **A tres años la mediana del intervalo se duplica**, de 6,2 a 13,7 puntos, y en Meta y Putumayo supera
   los 40. El deterioro con el horizonte no es un detalle de nota al pie.

## Decisión

1. **El ancho del intervalo se publica como indicador propio**, `intervalo_ancho_proy`, junto al valor
   central. No se deriva en el navegador a partir del tamaño, de la región ni de ninguna otra heurística:
   la medición de arriba muestra que cualquier sustituto se equivocaría.
2. **La opacidad del relleno codifica la confianza.** El color da el crecimiento proyectado en escala
   divergente; la opacidad es inversa al ancho del intervalo. Los departamentos donde el modelo sabe poco
   se ven apagados sin que el lector tenga que interactuar con nada.
3. **Los años proyectados se distinguen de los observados con una trama**, no solo con la leyenda. Al
   seleccionar 2026, 2027 o 2028 el relleno lleva una trama diagonal. El JSON de series gana un campo
   `anios_proyectados` para que el navegador sepa dónde termina el dato y empieza el pronóstico.
4. **La capa de ancho del intervalo también es seleccionable como vista propia**, para quien quiera mirar
   directamente dónde el modelo es débil.
5. **La tabla de backtest se publica junto al mapa, no en un anexo.** R-09 obliga a que toda cifra publicada
   trace a una prueba; aquí además es lo que permite juzgar el mapa. Incluye la comparación del origen 2020
   de ADR-020, donde declarar los atípicos no cambia ni un decimal, y el punto de equilibrio del ancla de
   ADR-021.
6. **Ninguna capa de proyección se publica sin su capa de incertidumbre.** Es una condición de publicación,
   no una recomendación: si `intervalo_ancho_proy` falta o no cuadra con el número de unidades y años, la
   exportación falla.

## Alternativas consideradas

- **Publicar solo el valor central y explicar la incertidumbre en el texto.** Es lo que hace casi todo el
  mundo y es la razón por la que estos mapas se citan mal: el texto no viaja con la captura de pantalla.
- **Opacidad por tamaño del departamento.** Es más simple y está mal: ρ = −0,358, con Meta y Amazonas como
  contraejemplos directos.
- **Franjas de confianza discretas** (alta, media, baja) en vez de opacidad continua. Se leen más rápido y
  esconden que el ancho varía siete veces; además el umbral entre franjas sería un parámetro arbitrario
  más que discutir.
- **Mostrar el intervalo solo al pasar el cursor.** Deja fuera al lector que mira el mapa en una imagen, en
  el móvil, o en una presentación de otra persona, que es como se consume la mayor parte del tiempo.
- **No publicar 2028 por ser demasiado incierto.** ADR-019 ya fijó que a tres años el modelo todavía aporta
  sobre una deriva. El problema de 2028 no es que no valga, es que hay que verlo con su intervalo, que es
  precisamente lo que este ADR resuelve.

## Consecuencias

- `config/atlas.yaml` gana un grupo `proyeccion` con tres indicadores: crecimiento proyectado del PIB real,
  crecimiento proyectado por habitante y ancho del intervalo. Los tres, escala divergente los dos primeros
  y secuencial el tercero.
- El presupuesto de 3 MB de `atlas/data/` no corre peligro: 33 unidades × 3 años × 3 indicadores son unos
  300 números. El que consume presupuesto es el nivel municipal, que esta capa no toca.
- `components/atlas/render.ts` en el sitio tiene que aprender opacidad variable y trama. Es el cambio de
  mayor superficie de toda la capa, y vive en el repositorio del sitio, no en este.
- La decisión 6 añade una comprobación a la exportación que puede romper la publicación. Es deliberado:
  es el mismo papel que `qa_deposito.py` cumplía para el documento de la tesis.
- Al publicar la versión anclada y la sin anclar (ADR-021) más el ancho del intervalo, el selector del
  atlas crece. Hay una deuda de diseño de interfaz que este ADR no resuelve y que conviene no dejar
  crecer más.

## Cómo revertirla

Quitar el grupo `proyeccion` de `config/atlas.yaml` devuelve el atlas a lo que publica hoy; la
comprobación de la decisión 6 se desactiva con él. Los cambios de `render.ts` en el sitio son
independientes y se revierten por separado.
