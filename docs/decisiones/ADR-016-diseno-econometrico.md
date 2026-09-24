# ADR-016 · Diseño econométrico del panel departamental

- Fecha: 2026-09-07
- Estado: aceptada

## Contexto

La pregunta es si la inclusión financiera predice el crecimiento del producto real per cápita de los
departamentos. El panel es anual, 33 departamentos por 8 años (2018 a 2025), con la dependiente disponible
desde 2019 porque el crecimiento necesita el nivel anterior: 231 observaciones de crecimiento y 228 con el
índice y los controles.

Un panel así tiene tres trampas conocidas antes de mirar un solo coeficiente. Los departamentos comparten
la política monetaria, el tipo de cambio y la pandemia, así que sus errores no son independientes. El
índice sube en todos ellos a la vez, así que cualquier variable que también suba con los años se le
parece. Y 33 clústeres no bastan para que el error estándar agrupado se comporte como promete su asintótica.

## Decisión

1. **Especificación base**: crecimiento del PIB real per cápita sobre el índice compuesto, con efectos
   fijos de entidad **y** de tiempo, más el logaritmo del ingreso rezagado (convergencia condicional) y la
   tasa de urbanización. Errores agrupados por departamento y, al lado, Driscoll-Kraay, que admite
   dependencia entre departamentos en el mismo año.
2. **El contraste sin efectos de tiempo se publica**, no como alternativa sino como demostración: la
   diferencia entre los dos coeficientes es la parte que era tendencia nacional.
3. **Diagnósticos medidos, no supuestos**: CD de Pesaran sobre los residuos, CIPS sobre el índice —con
   T = 8 se lee como indicio y se dice—, I de Moran por año sobre el crecimiento con inferencia por
   permutación y contigüidad leída de los arcos compartidos del TopoJSON.
4. **Cuatro diseños que no dependen de que el índice sea exógeno**: CCE de Pesaran con cargas
   heterogéneas por departamento (sin efectos de tiempo, que serían redundantes con las medias), shift-share
   con la exposición de **2018** —anterior a cualquier observación de la dependiente— por la adopción
   nacional, estudio de eventos alrededor de 2020, y SLX con el rezago espacial del índice.
5. **El shift-share se contrasta contra sí mismo**: con efectos de tiempo identifica una pendiente
   diferencial de los departamentos más expuestos al principio, y esa pendiente la produciría igual
   cualquier condición inicial correlacionada con el índice. Se estima con el ingreso y la urbanización
   iniciales como exposiciones de placebo, y en carrera de caballos con el ingreso inicial. Solo cuenta lo
   que sobreviva a los tres.
6. **Inferencia con pocos clústeres**: bootstrap salvaje por clúster con la nula impuesta (Rademacher,
   999 réplicas) y placebo por permutación del índice dentro de cada año (499 réplicas).
7. **Sensibilidad**: las tres dimensiones por separado, la especificación en cambios del índice, y los
   índices alternativos por PCA y por distancia de Sarma.
8. Toda cifra publicada sale de `data/processed/econ/resultados.json`, que escribe `uv run iif econ`
   (R-09); ningún número viene de un cuaderno.

## Alternativas consideradas

- SAR o SDM por máxima verosimilitud: exigen supuestos de estructura espacial que un panel de ocho años no
  puede sostener; SLX responde a la misma pregunta —¿el vecindario explica el coeficiente?— con OLS.
- GMM de Arellano-Bond: con T = 8 y N = 33 la proliferación de instrumentos vacía la prueba de Hansen; no
  aporta nada que el diseño en cambios y el CCE no digan más limpio.
- Estudio de eventos con contraste de tendencias previas: no es posible; la dependiente empieza en 2019 y
  el choque es 2020, así que solo hay un año previo y es el de referencia. Se publica con esa limitación
  escrita, no se esconde.

## Consecuencias

- El resultado principal puede ser nulo y se publica igual, con su N, sus clústeres y sus pruebas.
- La batería entera corre en segundos sobre DuckDB; se repite en CI cada vez que cambia el panel o el
  índice, y las pruebas sintéticas (`tests/test_econ.py`) garantizan que cada estimador encuentra lo que
  hay cuando se sabe lo que hay.
- Un coeficiente que sobreviva solo a un diseño de los cuatro no se presenta como efecto.

## Cómo revertirla

La especificación vive en `src/iif/econ/run.py` (`CONTROLES`, `ANIO_BASE`, `ANIO_EVENTO`); cambiarla es
cambiar esas constantes y volver a correr `uv run iif econ`. Los diseños son funciones independientes en
`designs.py` y se pueden quitar de la batería sin tocar los demás.

## Adenda 2026-09-23: lo que cambió después de la decisión

Esta adenda no reescribe el cuerpo de arriba, que describe lo que se decidió el 2026-09-07. Registra en qué
se separa hoy la batería de ese texto.

1. **El placebo del punto 6 ya no baraja dentro de cada año.** Desde B-074 (numerada B-054 en la rama
   original `auditoria-potencia-y-denominador` y renumerada al fusionar), el placebo reasigna la
   trayectoria completa de cada departamento: barajar dentro del año destruía también la correlación
   serial del índice y producía una nube tres veces demasiado estrecha. El cambio se hizo después de ver
   que el placebo antiguo rechazaba (p = 0,038) donde el error agrupado y el bootstrap no; el argumento
   técnico es correcto, y por eso el modo antiguo sigue publicado al lado como diagnóstico.
2. **El bootstrap del punto 6 se studentiza con el error agrupado**, no con el homocedástico, y se publica
   también con pesos de Webb y con el intervalo por inversión (ADR-024).
3. **Driscoll-Kraay (punto 1) pasa a nota.** Con T = 7 no es creíble como inferencia.
4. **El "shift-share" del punto 4 se llama diseño de exposición inicial**, y los diseños del punto 4 dejan
   de presentarse como "que no dependen de la exogeneidad": el de exposición inicial la exige para el
   nivel de 2018, y su placebo de urbanización muestra que no se cumple.
5. **Las tendencias previas sí se contrastan.** La alternativa descartada ("no es posible") era un
   artefacto de construcción: la exposición es fija en 2018 y el PIB real existe desde 2005. ADR-024
   añade el contraste.
6. **La carrera del punto 5** se corre contra el ingreso y contra la urbanización iniciales, y contra las
   dos a la vez, no solo contra el ingreso.
