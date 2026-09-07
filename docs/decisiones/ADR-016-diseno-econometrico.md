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
