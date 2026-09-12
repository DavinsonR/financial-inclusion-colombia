# ADR-018 · Un nulo se publica con su potencia y con su prueba de equivalencia

- Fecha: 2026-09-11
- Estado: aceptada

## Contexto

El resultado principal del proyecto es un nulo: con efectos fijos de entidad y tiempo, el índice de
inclusión financiera no predice el crecimiento del PIB real per cápita departamental (β = +0,00074,
SE = 0,00597, p = 0,90). ADR-016 previó que el resultado pudiera ser nulo y decidió publicarlo igual, con
su N, sus clústeres y sus pruebas. Eso se cumplió.

Lo que no se previó es que un nulo necesita una cifra más para significar algo. Un contraste que no rechaza
la nula no distingue entre "el efecto es cero" y "el diseño no vería el efecto aunque existiera". La
diferencia entre las dos lecturas es el efecto mínimo detectable, y en el repositorio no existe: las
palabras potencia, MDE y equivalencia no aparecen en ningún archivo salvo para decir que la prueba CD y la
CIPS tienen poca potencia con T corto.

Tres mediciones sobre la muestra de estimación fijan el tamaño del problema:

1. **Los efectos fijos de dos vías destruyen el 92 % de la varianza del índice.** La desviación típica del
   compuesto pasa de 1,2171 en el panel completo a 0,3337 una vez quitadas las medias de departamento y de
   año y residualizado contra los controles. Esa última es la que identifica el coeficiente. El 46 % de la
   varianza está entre departamentos y el 54 % entre años; sobra el 8 %.
2. **El MDE al 80 % de potencia es 0,0167 en unidades del índice**, que son 0,56 puntos porcentuales de
   crecimiento anual por desviación típica identificante (2,04 pp por desviación bruta).
3. **El intervalo de confianza al 95 % es [−0,0111, +0,0125]**, o [−0,37, +0,42] puntos porcentuales por
   desviación identificante.

La prueba de equivalencia (TOST) sobre esos números dice algo más preciso que el p-valor: el diseño
descarta efectos mayores que ±0,50 pp por desviación (p = 0,009) y **no** descarta efectos de ±0,25 pp
(p = 0,13).

## Decisión

1. **La afirmación principal del proyecto deja de ser "el índice no predice el crecimiento" y pasa a ser la
   cota.** El texto publicado dice qué efectos descarta el diseño y cuáles no puede descartar. "No predice"
   es una afirmación que estos datos no sostienen; "descarta efectos por encima de medio punto porcentual
   por desviación típica y no puede pronunciarse por debajo de un cuarto de punto" sí.
2. **`resultados.json` gana un bloque `potencia`** con el MDE a 80 % y a 50 %, la desviación típica bruta y
   la identificante del regresor, el intervalo de confianza traducido a puntos porcentuales, y el TOST en
   tres márgenes. Sale del mismo `uv run iif econ` que todo lo demás (R-09).
3. **La descomposición de varianza del regresor se publica al lado**, porque es la explicación de por qué
   el MDE es el que es: sin ella, un lector no sabe si el diseño es débil por la muestra o por el estimador.
4. **El módulo vive en `src/iif/econ/power.py`** y se prueba sobre casos con respuesta conocida, igual que
   el resto de la batería.
5. **Ninguna cifra de potencia se calcula a mano ni se cita de memoria.** El MDE depende del error estándar
   publicado, y el error estándar cambia cuando cambia la especificación: recalcularlo es parte de la
   corrida, no una nota escrita una vez.

## Alternativas consideradas

- **Potencia ex ante, simulando antes de ver los datos.** Es lo correcto en un preregistro y aquí llega
  tarde: el trabajo ya está estimado. La potencia retrospectiva calculada sobre el propio coeficiente
  estimado es una práctica desaconsejada (es una transformación monótona del p-valor y no aporta nada);
  la que se publica aquí no es esa, sino el MDE, que depende del error estándar y no del coeficiente, y
  que sí es informativo.
- **Solo el intervalo de confianza, sin TOST.** El intervalo ya dice casi todo y es más fácil de leer. Se
  publican los dos porque el TOST responde a la pregunta que un lector hace de verdad —¿puedo descartar un
  efecto de este tamaño?— con un p-valor que no se presta a la lectura de "el cero está dentro".
- **Fijar el margen de equivalencia desde la literatura.** Sería lo ideal y exige un tamaño de efecto previo
  defendible que el repositorio todavía no tiene, porque no hay bibliografía (queda pendiente). Mientras
  tanto se publican tres márgenes y se deja que el lector escoja el suyo.

## Consecuencias

- El ancla `main-result` del README cambia de redacción en las dos versiones del archivo, conservando el
  ancla (R-12).
- El nulo se vuelve más defendible, no menos: hoy dice algo que el diseño no puede sostener; después dirá
  algo que sí, con su número.
- Aparece una cota explícita que un trabajo posterior puede intentar bajar. Es la justificación cuantitativa
  para el panel municipal y para el panel trimestral con ITAED que ADR-001 dejó pendiente: cualquiera de
  los dos se juzga por cuánto baja el MDE, no por cuántas filas añade.

## Cómo revertirla

Quitar el bloque `potencia` de `src/iif/econ/run.py` y el módulo `power.py`. La redacción del README es
independiente y habría que revertirla a mano.
