# ADR-017 · El denominador de las variables monetarias del índice

- Fecha: 2026-09-11
- Estado: aceptada

## Contexto

ADR-015 normaliza las variables monetarias del índice como porcentaje del producto: el PIB corriente
departamental en el panel departamental y el valor agregado corriente en el municipal. Es la definición
estándar de profundidad financiera y la justificación sigue siendo buena: dos series nominales divididas
entre sí no necesitan deflactor.

El problema no es la razón, es *cuál* producto va en el denominador. Cinco de las ocho variables del índice
llevan el producto abajo (`monto_total`, `saldo_total_cta_ahorros`, `monto_total_cred_consumo`,
`monto_total_cred_vivienda`, `monto_total_micro`), y la variable dependiente de la econometría es el
crecimiento del logaritmo del PIB real per cápita. El mismo producto está en el denominador del regresor y
en el numerador de la dependiente. Cuando el producto cae, el índice sube por aritmética y el crecimiento
baja por definición: eso es una correlación negativa fabricada por la construcción, no medida en los datos.

Tres mediciones sobre el panel construido dimensionan el problema:

1. **Un índice placebo sin contenido financiero produce un coeficiente significativo.** Congelando los
   numeradores de las cinco variables monetarias en su valor de 2018 y dejando que solo se mueva el
   denominador, el índice resultante —que por construcción no contiene ninguna información sobre
   inclusión financiera— da β = −0,2525 con p = 0,0007 en la especificación publicada.
2. **Los coeficientes por dimensión cambian de signo con el denominador.** Con el PIB contemporáneo,
   profundidad da −0,0208 y uso −0,0037. Con el PIB rezagado, −0,0056 y +0,0104. Con el PIB de 2018 fijo,
   +0,0104 y +0,0014.
3. **El compuesto no cambia de veredicto.** +0,00074 (p = 0,90) con el contemporáneo, +0,00378 (p = 0,54)
   con el rezagado, +0,00530 (p = 0,34) con el fijo. El resultado principal es nulo en los tres.

El tercer punto es el que ordena la decisión: lo que está en juego no es la conclusión del trabajo, son las
tres cifras por dimensión que hoy se publican al lado, y que hoy son artefacto.

## Decisión

1. **El denominador principal pasa a ser el producto rezagado un año.** Un año de separación rompe la
   simultaneidad: el crédito de 2022 se mide contra el tamaño de la economía en 2021, que ya estaba
   determinado cuando el crédito se otorgó. La lectura de "profundidad financiera" se conserva entera.
2. **El denominador se declara en `config/index.yaml`** con la clave `denominador`, que admite
   `contemporaneo`, `rezagado` y `fijo`. No es una constante escondida en Python (R-15).
3. **Las tres versiones se publican como sensibilidad**, con el índice placebo de solo-denominador al
   lado. Un lector tiene que poder ver cuánto del coeficiente era el denominador, no creerlo de palabra.
4. **La primera observación de cada unidad se pierde** en las variables monetarias, porque el rezago no
   existe en 2018. El índice arranca en 2019 para esas cinco variables. Como la muestra de estimación ya
   empieza en 2019 —el crecimiento necesita el nivel anterior—, la econometría no pierde ni una fila; lo
   que se pierde es el año 2018 del atlas para esas variables, y se marca como no observado en vez de
   rellenarse (R-13).
5. **Los pesos se recalibran sobre la ventana con el denominador nuevo** y se vuelven a congelar. Cambiar
   el denominador cambia la escala de las variables, así que las medias y desviaciones de 2018-2019 dejan
   de valer. Es una recalibración explícita, que es exactamente lo que ADR-015 punto 6 exige.

## Alternativas consideradas

- **Producto fijo del año base (2018).** Elimina el denominador como fuente de variación por completo, que
  es la propiedad más limpia de las tres. Se descarta como principal porque el índice dejaría de medir
  profundidad relativa al tamaño *actual* de la economía: un departamento que duplicó su producto y duplicó
  su crédito aparecería como si se hubiera profundizado, cuando no lo hizo. Se conserva como sensibilidad.
- **Normalizar los montos por población, como los conteos.** Hace comparable todo el índice bajo una sola
  regla y elimina el producto del denominador de raíz. Se descarta porque un monto por habitante no es
  profundidad financiera: es tamaño del crédito per cápita, que ya mide otra cosa y que correlaciona con el
  ingreso por construcción.
- **Dejar el contemporáneo y advertirlo en el texto.** Se descarta por R-09: una cifra publicada que se sabe
  contaminada no se arregla con una nota al pie. La advertencia escrita no es una corrección implementada.
- **Deflactar numerador y denominador.** No resuelve nada: el problema es la simultaneidad del denominador,
  no su unidad, y deflactar dos series nominales por el mismo índice deja la razón idéntica.

## Consecuencias

- Las tres cifras por dimensión del README cambian y hay que reescribir esa tabla, además del párrafo que
  las interpreta. El resultado principal y su lectura no cambian.
- El índice publicado en `data/processed/indice_*.parquet` y en el atlas cambia de valores. El atlas hay
  que reexportarlo (`uv run iif atlas`) y su presupuesto de 3 MB hay que volver a comprobarlo.
- `config/index.yaml` gana la clave `denominador` y sus `pesos_congelados` se reescriben. El cambio queda
  en git, que es donde debe quedar.
- Aparece una prueba nueva que fija el sesgo: el índice placebo de solo-denominador tiene que dar un
  coeficiente significativo con el denominador contemporáneo y dejar de darlo con el rezagado. Si algún día
  esa prueba se pone verde con el contemporáneo, es que el panel cambió y hay que volver a mirar.

## Cómo revertirla

Poner `denominador: contemporaneo` en `config/index.yaml`, correr `uv run iif index --recalibrar` y volver
a exportar el atlas. Las pruebas de reproducibilidad del índice avisan del cambio de pesos.
