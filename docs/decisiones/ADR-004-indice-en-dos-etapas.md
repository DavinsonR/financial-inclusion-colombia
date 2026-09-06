# ADR-004 · Índice en dos etapas, pesos congelados, estandarización, internet fuera, CAE excluidas del panel largo

- Fecha: 2026-09-06
- Estado: aceptada

## Contexto

El índice de la tesis era un PCA sobre 9 variables con 4 componentes (regla del 80 %). Los pesos implícitos por variable, que el notebook nunca imprimió, dan microcrédito −0,231 y transferencias −0,006 (B-005). El escalado min-max más EPS creó un outlier de 9,8 desviaciones en log(IIF) (B-006). La orientación de signo se verificaba de forma circular (B-007). Internet entraba como variable de inclusión financiera siendo infraestructura, con 50 ceros que eran faltantes (B-004). El jurado pidió desagregación por dimensión y por variable.

Las cuentas de ahorro electrónicas (CAE) existen en `ptgf-ywrb` (2017Q4 a 2021Q1); su continuidad en `kx2f-xjdq` está por confirmar contra el diccionario de esa tabla, porque la regulación las reemplazó por depósitos de bajo monto.

## Decisión

1. Índice en dos etapas (Cámara y Tuesta): un PCA por dimensión (acceso, uso, profundidad) produce tres subíndices; el compuesto combina los subíndices. Así hay descomposición por dimensión y por variable.
2. Retención por Kaiser dentro de cada dimensión; los pesos implícitos por variable se publican siempre y una prueba exige signo no negativo para cada variable de inclusión.
3. Orientación a priori: cada variable se codifica de modo que más valor sea más inclusión; no hay verificación por correlación con una referencia.
4. Pesos ajustados en la ventana inicial (2018 a 2019) y congelados para el resto de la serie. El índice de años posteriores no cambia cuando llegan datos nuevos.
5. Estandarización (media 0, desviación 1 en la ventana de ajuste) en vez de min-max. Sin logaritmo del índice.
6. Internet queda fuera del índice; puede entrar como control.
7. Las CAE quedan fuera del panel largo (2018 a 2025) hasta que el empalme con kx2f se valide; dentro de la ventana ptgf se usan como sensibilidad.
8. Alternativas publicadas junto al índice: pesos iguales por dimensión e índice de distancia de Sarma.

## Alternativas consideradas

- Mantener el PCA único: no da la descomposición pedida y arrastra los pesos negativos.
- Pesos iguales solamente: transparente, pero ignora la correlación entre variables; se publica como alternativa, no como principal.
- Índice de Sarma como principal: exige elegir umbrales normativos por variable; se publica como alternativa.

## Consecuencias

- El índice de la tesis y el nuevo no son comparables en nivel; la comparación va en `mart_legacy_vs_ptgf` (fase 2).
- El atlas puede mostrar dimensión, subíndice y aporte de cada variable.
- La ventana congelada obliga a rehacer el índice completo si cambia la lista de variables (es intencional).

## Cómo revertirla

`config/index.yaml` declara dimensiones, variables, regla de retención, ventana y escalado. Cambiarlo regenera el índice; la prueba de signo y la de pesos publicados siguen activas salvo ADR nuevo.
