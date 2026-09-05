# Decisiones metodológicas de la versión corregida (agosto de 2026)

Registro de las decisiones que distinguen la versión radicada de la versión evaluada. Cada una se enuncia con su motivo; el detalle está en el documento del trabajo de grado.

## 1. Efectos fijos de tiempo: la especificación de referencia es two-way FE

El modelo con efectos fijos de entidad **y** de tiempo pasa a ser la especificación de referencia. Bajo ella el coeficiente del IIF deja de ser significativo (β = −0,15; p = 0,984). Ese resultado se presenta como hallazgo central, junto con la estimación en la submuestra prepandemia, la prueba de Pesaran (CD) y los errores estándar de Driscoll-Kraay. Motivo: los choques comunes a todos los departamentos en el periodo (entre ellos la pandemia) no pueden atribuirse al índice.

## 2. El rezago del IIF ordena, no identifica

El rezago del índice constituye un ordenamiento temporal, no una estrategia de identificación causal. El lenguaje se atenúa en todo el documento (resumen, abstract y secciones de resultados): se habla de predicción, no de efecto causal.

## 3. Sesgo de Nickell, cuantificado

Con T = 14 y ρ̂ = 0,4279 el sesgo del panel dinámico se cuantifica explícitamente. El coeficiente del IIF se mantiene significativo en el modelo estático sin el rezago del crecimiento, con una magnitud cercana a la mitad. Se documenta por qué el GMM dinámico no ofrece una alternativa superior en este panel: con pocos individuos y muchos instrumentos el estimador pierde las propiedades que lo justificarían.

## 4. Variable dependiente: PIB real per cápita

La variable principal pasa a ser el crecimiento del PIB real per cápita departamental. El PIB agregado queda solo como ejercicio de robustez. Motivo: el crecimiento agregado mezcla dinámica demográfica con dinámica productiva.

## 5. Índice validado = índice utilizado

El índice principal (IIF_Multidim) coincide exactamente con el validado: 4 componentes, 84,4 % de la varianza. El índice basado solo en PC1 pasa a ser un ejercicio de robustez secundario. Motivo: validar un índice y estimar con otro rompe la cadena de evidencia.

## 6. Consistencia interna

Se corrigió la suma de observaciones regionales en la tabla correspondiente, se unificó la cifra de semi-elasticidad, se verificó la numeración cruzada de tablas y se añadieron fuentes puntuales para las cifras de la introducción.

---

Pendiente de precisar en este repositorio cuando se suban los datos: la frecuencia intra-anual que produce T = 14 por departamento dentro de 2017–2021, y las fuentes primarias de cada dimensión del índice.
