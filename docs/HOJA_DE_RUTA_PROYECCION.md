# Hoja de ruta - proyeccion del crecimiento departamental y capa de mapa

> Rescatado de la sesión del 18-sep-2026 y renumerado: los ADR pasan a 019-022,
> porque 017 (denominador del índice) y 018 (potencia y equivalencia) están reservados para la
> rama `auditoria-potencia-y-denominador`, pendiente de fusión.
>
> **Estado al 23-sep-2026.** Hechas: fase 0 (ADR-019 a ADR-022), el motor (`src/iif/forecast/`:
> `frame.py`, `models.py`, `backtest.py`, `anchor.py`, `reconcile.py`, `run.py`; comando
> `uv run iif forecast`, salida en `data/processed/forecast/resultados.json`) y la exportación al
> atlas (grupo `proyeccion` de `config/atlas.yaml`). Pendientes: el *nowcast* con ITAED y
> shift-share, la página de `metodologia/` con la tabla de backtest y el render en el sitio.
> Los nombres de archivo de la §6 son los del plan; los reales son los de arriba. El texto que
> sigue es el plan original y se conserva como registro.

**Autor del plan:** sesión de trabajo del 18-sep-2026
**Repos afectados:** `financial-inclusion-colombia` (motor) · `proyecto-davirson` (sitio)
**Estado:** propuesta del 18-sep-2026; ver el estado actual en la nota de cabecera.

---

## 0. Resumen en diez líneas

La tesis está cerrada y su conclusión es un **nulo**: el índice de inclusión financiera no
predice el crecimiento del PIB departamental. Ese nulo restringe este proyecto más de lo que
parece, y es el primer hallazgo del plan: **el IIF no puede entrar como regresor del modelo de
proyección**, porque publicar un pronóstico que lo usa contradice el resultado que ya
publicaste.

Lo que sí es viable, y lo verifiqué con los datos reales: un ARIMA por departamento sobre el
PIB real 2005–2025, **anclado a la proyección nacional del consenso de analistas y reconciliado
jerárquicamente**. En backtest 2024–2025 le gana a la caminata aleatoria por un margen modesto
pero consistente — y solo si 2020 y 2021 se tratan como atípicos. Sin esa corrección, el ARIMA
pierde contra el pronóstico ingenuo.

El mapa de calor no es trabajo nuevo de infraestructura: el contrato `atlas.yaml → iif atlas →
public/atlas/*.json → Atlas.tsx` ya existe y ya alimenta el mapa del IIF. Se extiende, no se
construye.

---

## 1. Diagnóstico — qué hay realmente

### 1.1 Los insumos que ya existen en este repositorio

Todo lo que la capa de proyección necesita está ya adquirido y parseado aquí, en Parquet.
No hace falta ninguna fuente nueva para el pronóstico base; el ancla nacional (ADR-021) sí
es una fuente nueva.

| Insumo | Archivo | Cobertura | Estado |
|---|---|---|---|
| PIB departamental real (base 2015) | `data/interim/dane/pib_departamento_anual.parquet` | 2005–2025 · 33 deptos · 693 filas · **0 nulos** | listo |
| Valor agregado por actividad | `va_departamento_actividad_anual.parquet` | 2005–2025 · 33 × 15 actividades | listo |
| ITAED trimestral | `itaed_departamento_trimestre.parquet` | 2015T1–2026T1 · **solo 15 unidades** | listo |
| Proyecciones de población | `poblacion_departamento_anual.parquet` | **2018–2050** · 33 deptos | listo |
| Índice IIF departamental | `data/processed/indice_departamento_anual.parquet` | 2018–2025 · 264 filas | listo |
| Geometría MGN 2024 | `data/interim/mgn/departamentos.parquet` | 33 deptos · 1.121 municipios | listo |

**Tres consecuencias operativas:**

1. **La población ya está proyectada hasta 2050.** El denominador per cápita se conoce de
   antemano. Solo hay que pronosticar el PIB; el per cápita sale por división. Esto elimina
   la mitad del problema y casi nadie lo aprovecha.

2. **2024 es `provisional` y 2025 es `preliminar`.** El DANE los va a revisar. Un backtest que
   los use como verdad queda contaminado en cuanto salga la revisión. Hay que guardar la
   *vintage* de cada corrida desde el día uno, o el histórico de desempeño no valdrá nada
   dentro de un año.

3. **El ITAED cubre 15 unidades, no 33** — Antioquia, Atlántico, Bogotá, Bolívar, Boyacá,
   Casanare, Cesar, Cundinamarca, La Guajira, Meta, Santander, Tolima, Valle, más "Colombia" y
   un agregado "Resto". Es la única serie subnacional de alta frecuencia que existe en
   Colombia. Sirve para *nowcasting* de 13 departamentos; los otros 20 quedan sin señal
   trimestral y hay que tratarlos por otra vía.

### 1.2 La jerarquía cierra, y eso habilita el método correcto

Comprobé si los 33 departamentos suman el total nacional del DANE:

| Año | Brecha suma-deptos vs nacional |
|---|---|
| 2018–2023 | entre −0,023 % y +0,038 % |
| 2024 | +0,024 % |
| 2025 | +0,072 % |

Brecha máxima **0,07 %** en la ventana 2018–2025. Sobre 2005–2025 la brecha máxima es **1,28 %
(2009)** y los años 2005–2012 van de 0,23 % a 1,28 %, por la retropolación del DANE (B-049;
`coherencia_jerarquica_pct` en `data/processed/forecast/resultados.json`). La jerarquía es
coherente en la práctica en la ventana donde se reconcilia. Esto no es un detalle: es
lo que hace legítima la reconciliación jerárquica de la §3. Si la brecha fuera del 3 % habría
que resolver primero un problema de conciliación contable.

### 1.3 La concentración cambia el significado del ancla

Peso en el PIB nacional, 2023:

| Departamento | % |
|---|---|
| Bogotá D.C. | 26,70 |
| Antioquia | 14,95 |
| Valle del Cauca | 9,97 |
| Santander | 6,31 |
| Cundinamarca | 6,11 |
| Atlántico | 4,56 |
| **Suma de los 15 más pequeños** | **7,18** |

Los tres primeros son el 51,6 % del país. **Anclar al total nacional fija, en la práctica, a
Bogotá, Antioquia y Valle.** Los 15 departamentos pequeños suman 7,2 % y el ancla casi no los
toca: ahí el pronóstico es puro ARIMA y ahí está toda la incertidumbre.

Consecuencia para el mapa: las zonas donde el color va a ser menos confiable son exactamente
las periféricas — Amazonía, Orinoquía, Chocó, San Andrés. El mapa tiene que decirlo.

---

## 2. Viabilidad del ARIMA — medida, no supuesta

> **Superado por ADR-020.** Las cifras de esta seccion vienen de una sola particion
> (entrena hasta 2023, pronostica 2024-2025). ADR-020 rehizo la medicion con origen movil
> sobre 2018-2025 y prueba de Diebold-Mariano: 264 pares por modelo en vez de 66, y una
> conclusion mas precisa. Para citar numeros, usar ADR-020.


Regla R-17 del repo: antes de elegir un método se mide su supuesto. Lo hice.

**Diseño:** entrenamiento con datos definitivos hasta 2023 (19 observaciones anuales por
departamento), pronóstico de 2024–2025, error contra el dato publicado. 33 departamentos.
Error = diferencia absoluta en el nivel logarítmico, en puntos porcentuales.

| Especificación | MAE medio (pp) | MAE mediano | ¿Le gana al ingenuo? |
|---|---|---|---|
| **ARIMA(1,1,0) + dummies COVID/rebote** | **1,99** | 1,53 | **sí** |
| ARIMA(1,1,1) + dummies | 2,01 | 1,52 | sí |
| ARIMA(0,1,1) + dummies | 2,17 | 1,57 | sí |
| *Ingenuo (último crecimiento)* | *2,26* | *2,02* | — |
| ARIMA(2,1,0) + dummies | 2,27 | 1,44 | apenas |
| ARIMA(0,1,0) deriva | 2,67 | 2,23 | no |
| *Deriva (media histórica)* | *2,67* | *2,23* | — |
| ARIMA(1,1,1) **sin** dummies | 2,80 | 2,68 | **no** |
| ARIMA(1,1,0) **sin** dummies | 2,84 | 2,60 | **no** |
| Deriva de 3 años | 5,76 | 5,57 | no, desastroso |

### Los tres hallazgos que definen el diseño

**1. Sin tratar el COVID, el ARIMA pierde contra la caminata aleatoria.** Es el resultado más
importante de esta prueba. La caída de −7,5 % en 2020 y el rebote de +10,3 % en 2021 envenenan
la estimación de los parámetros autorregresivos: el modelo aprende un ciclo que no existe. Con
dos variables exógenas que absorben esos dos años, el mismo ARIMA pasa de 2,84 a 1,99 pp.

**2. La ganancia sobre el ingenuo es del 12 %.** De 2,26 a 1,99 pp. Es real y es consistente
(se sostiene también en la mediana: 2,02 → 1,53), pero no es un triunfo. **Hay que decirlo
así.** Con 20 observaciones anuales por departamento no se puede prometer más, y prometer más
es exactamente el error que un evaluador detectaría.

**3. Para 10 de los 33 departamentos el ingenuo sigue siendo el mejor.** No hay una
especificación única que gane en todas partes. Esto obliga a una de dos: selección por
departamento vía criterio fuera de muestra, o combinación de pronósticos. Recomiendo
**combinación** — promediar ARIMA, ingenuo y deriva es más estable que elegir el ganador de un
backtest de dos años, que es una muestra demasiado corta para seleccionar con confianza.

### Lo que NO va en el modelo

**El IIF no entra como regresor.** Tu propia tesis, en nueve especificaciones independientes,
concluye que no predice el crecimiento. Meterlo ahora como variable explicativa del pronóstico
sería incoherente con lo que publicaste y con el resultado del repo (β ≈ +0,0007, p = 0,90).

En el mapa las dos capas conviven — inclusión financiera y crecimiento proyectado, lado a lado,
y el lector puede ver que no se parecen. Eso es **más honesto y más interesante** que fingir
una relación: es la ilustración visual de tu propio hallazgo nulo.

---

## 3. El cruce con analistas y entidades — arquitectura

### 3.1 El problema que nadie menciona

**En Colombia nadie publica proyecciones de PIB departamental.** Ni el Banco de la República,
ni Hacienda, ni el DNP, ni Fedesarrollo, ni ANIF, ni el FMI. Todas las proyecciones
disponibles son **nacionales**.

Esto significa que "cruzar con datos de analistas" no puede ser una comparación
departamento-contra-departamento: no existe el contrafactual. El cruce tiene que ser
**jerárquico**: el consenso nacional es un *ancla*, no un *rival*.

### 3.2 Arquitectura propuesta: abajo-arriba anclado y reconciliado

> **Superado por ADR-021 en un punto.** Esta seccion propone reconciliacion MinT.
> Medida contra el reparto proporcional al tamano sobre los mismos ocho origenes, MinT pierde:
> +21,3 % contra +41,2 % sobre el abajo-arriba. Se adopta el reparto proporcional.


```
   [33 ARIMA departamentales]          [consenso nacional de analistas]
      pronóstico base ŷ_i                      ancla ŷ_nac
              |                                     |
              +------------------+------------------+
                                 |
                   Reconciliación jerárquica (MinT / OLS)
                                 |
                 33 pronósticos coherentes: Σ ŷ_i = ŷ_nac
                                 |
                   ÷ población proyectada 2026–2050 (DANE)
                                 |
                   Crecimiento del PIB real per cápita
```

La reconciliación de Hyndman (MinT, *minimum trace*) es el método estándar y es
técnicamente correcto aquí porque la jerarquía cierra al 0,07 % en 2018–2025 (§1.2). Reparte la diferencia
entre la suma abajo-arriba y el ancla en proporción a la incertidumbre de cada serie: los
departamentos con ARIMA más errático absorben más ajuste, los estables menos. Es superior al
reparto proporcional simple y es defendible ante cualquiera.

### 3.3 Fuentes del ancla nacional

| Fuente | Qué aporta | Frecuencia | Acceso |
|---|---|---|---|
| **Banrep — EME** (Encuesta mensual de expectativas de analistas) | Consenso de PIB, inflación, tasa, TRM. Trae **dispersión** entre analistas | mensual | PDF/XLSX en banrep.gov.co |
| **MinHacienda — MFMP** | Senda oficial de PIB a 10 años, con supuestos fiscales | anual (junio) | PDF, extracción manual |
| **Fedesarrollo — EOF** | Encuesta de opinión financiera, consenso de mercado | mensual | PDF |
| **DNP** | Expectativas económicas, visión de planeación | periódico | web |
| **FMI — WEO** | Proyección a 5 años, comparable internacionalmente | semestral | **API pública** |
| **Banco Mundial / OCDE / CEPAL** | Contraste externo | semestral/anual | API / PDF |
| **DANE — ITAED** | *Nowcast* del año en curso para 13 deptos | trimestral | ya en el repo |

**La dispersión de la EME es el insumo más valioso y el más desaprovechado.** No sirve solo
para el escenario central: el mínimo y el máximo de los analistas dan escenarios pesimista y
optimista **con fuente citable**, en vez de inventados. Tres mapas, tres anclas, una sola
metodología.

### 3.4 Los proxies para el año en curso

El PIB departamental sale con ~12 meses de rezago. Para el año corriente:

- **13 departamentos + Bogotá:** ITAED trimestral. 45 trimestres de historia — ahí sí cabe un
  SARIMA de verdad, no el ARIMA justito de los datos anuales.
- **Los otros 20:** *shift-share* sectorial. Se conoce la composición de valor agregado por
  actividad (15 secciones CIIU, 2005–2025) y se proyecta el crecimiento nacional de cada
  sector sobre la mezcla de cada departamento. Un departamento minero y uno agrícola no
  responden igual al mismo ciclo nacional, y esto lo captura.
- **Puntos de atención SFC** (mensual, 2023→) y **accesos a internet MinTIC**: proxies de
  actividad de alta frecuencia, útiles como chequeo cruzado. No como regresores del PIB —
  vuelve el problema del §2.

---

## 4. Qué se publica en el sitio

### 4.1 El contrato ya existe

```
config/atlas.yaml  →  uv run iif atlas  →  atlas/data/*.json
                                              ↓ (copia)
                    Portfolio: public/atlas/*.json → components/atlas/Atlas.tsx
```

Presupuesto duro: **3 MB** para todo `atlas/data/`. Las series viajan como matrices año × unidad
redondeadas. Añadir proyecciones para 33 unidades × ~5 años × 3 indicadores es del orden de 500
números: **irrelevante frente al presupuesto**. El municipal (7.861 filas por indicador) es el
que consume; el departamental no.

### 4.2 Qué añadir

**En `config/atlas.yaml`, grupo nuevo `proyeccion`:**

| id | etiqueta | escala | decimales |
|---|---|---|---|
| `crecimiento_pib_real_proy` | Crecimiento proyectado del PIB real | divergente | 2 |
| `crecimiento_pib_real_pc_proy` | Crecimiento proyectado por habitante | divergente | 2 |
| `intervalo_ancho_proy` | Ancho del intervalo al 80 % | secuencial | 2 |

**En el JSON de series:** un campo `anios_proyectados: [2026, 2027, 2028]` para que el
navegador sepa dónde termina el dato y empieza el pronóstico.

### 4.3 La regla innegociable del mapa

**Un mapa de calor de un pronóstico puntual sin intervalo es una mentira por omisión.** Con
±2 pp de error medio y departamentos pequeños donde es mayor, pintar Vaupés de verde intenso
porque el punto central dice 3,1 % comunica una certeza que no existe.

Tres mecanismos, en orden de preferencia:

1. **Opacidad = confianza.** Color por valor central, opacidad inversa al ancho del intervalo.
   Los departamentos inciertos se ven apagados. Es inmediato y no necesita interacción.
2. **Capa conmutable de ancho del intervalo.** El indicador `intervalo_ancho_proy` como vista
   propia.
3. **Textura para años proyectados.** Trama diagonal sobre el relleno cuando el año
   seleccionado está en `anios_proyectados`. Distingue dato de pronóstico sin leer la leyenda.

Recomiendo **1 + 3 juntos**: el usuario ve de un vistazo que está mirando un pronóstico y dónde
ese pronóstico es débil.

La regla R-09 del repo — toda cifra publicada traza a una prueba — obliga además a que la tabla
de backtest de la §2 se publique junto al mapa. No como apéndice: como parte de la pieza.

---

## 5. El "proyecto auxiliar de variables macro" — recomendación

**No hagas un repo separado para las variables que alimentan este modelo.** El ancla nacional,
el VA sectorial, la población y el ITAED son *insumos* del pronóstico. Separarlos duplica la
capa de adquisición, rompe la regla R-15 (una sola fuente de verdad por constante) y te deja
dos manifiestos que se desincronizan en el primer mes.

**Lo correcto:** un módulo nuevo `src/iif/forecast/` y un grupo `macro:` en `config/sources.yaml`,
dentro del repo que ya existe. En el sitio, una **vista nueva del mismo atlas**, no un
proyecto nuevo.

**Ahora bien, sí hay un proyecto auxiliar que se justifica**, y es otro: un tablero
macroeconómico de Colombia con lo que *no* cabe en el mapa departamental — TRM, inflación,
tasa de intervención, desempleo, balanza, expectativas EME. Series nacionales de alta
frecuencia, sin geografía. Eso es una pieza distinta, con público distinto, y ahí sí un repo
propio tiene sentido. Pero es una decisión de portafolio, no una necesidad de este modelo.

Mi recomendación: **primero la capa de proyección dentro del repo actual; el tablero macro
después, si lo quieres como pieza de portafolio.**

---

## 6. Plan de ejecución

Las reglas del repo obligan a que las decisiones de valor pasen por un ADR antes del código
(R-11). Esto son cuatro ADR.

### Fase 0 — Decisiones registradas (1 sesión)

| ADR | Decisión |
|---|---|
| ADR-019 | Grano y horizonte del pronóstico: anual, 2026–2028, coherente con ADR-001 y R-05 |
| ADR-020 | Tratamiento de 2020–2021 como atípicos, con la evidencia del backtest de §2 |
| ADR-021 | Ancla nacional y reconciliación jerárquica MinT |
| ADR-022 | Cómo se publica la incertidumbre en el mapa |

### Fase 1 — Motor de pronóstico (2–3 sesiones)

- `src/iif/forecast/arima.py` — ajuste por departamento, dummies COVID/rebote, selección por
  AICc con tope de orden (p,q ≤ 2; con 20 observaciones no cabe más)
- `src/iif/forecast/benchmarks.py` — ingenuo, deriva, combinación
- `src/iif/forecast/backtest.py` — validación con ventana expansiva, origen móvil, salida a
  `data/processed/forecast/backtest.json`
- Tests: que ninguna especificación se publique si no le gana al ingenuo en el backtest. Es la
  puerta de calidad, equivalente a lo que `qa_deposito.py` hace en la tesis.

### Fase 2 — Ancla y reconciliación (2 sesiones)

- `config/sources.yaml`: grupo `macro` con FMI WEO (API) y los PDF de Banrep/Fedesarrollo
- `src/iif/forecast/anchor.py` — lectura del consenso, con escenarios central/mín/máx de la EME
- `src/iif/forecast/reconcile.py` — MinT sobre la jerarquía 33 → 1
- `src/iif/forecast/nowcast.py` — ITAED para 13 deptos, shift-share sectorial para los otros 20
- Test de coherencia: Σ departamentos = nacional, tolerancia 0,1 %

### Fase 3 — Publicación (1–2 sesiones)

- `config/atlas.yaml`: grupo `proyeccion`
- `src/iif/export/atlas.py`: emitir las series de pronóstico y `anios_proyectados`
- Verificar presupuesto de 3 MB
- Documento Quarto en `metodologia/` con la tabla de backtest

### Fase 4 — Sitio (2 sesiones)

- `components/atlas/types.ts`: tipos para años proyectados e intervalos
- `components/atlas/render.ts`: opacidad por confianza + trama para años proyectados
- Página de investigación: sección de proyección con la tabla de backtest visible
- `npm run check` — pasa por `check:artifacts` y `check:figures`, que van a exigir que los
  números del sitio tracen a un artefacto

**Total estimado: 8–11 sesiones de trabajo.**

---

## 7. Riesgos, dichos sin adornos

| # | Riesgo | Mitigación |
|---|---|---|
| 1 | **20 observaciones anuales por departamento es poco.** No hay forma de esquivarlo | Órdenes bajos (p,q ≤ 2), combinación en vez de selección, intervalos honestos, y decirlo en el sitio |
| 2 | **2024p y 2025pr se van a revisar.** El backtest se contamina retroactivamente | Guardar la *vintage* de cada corrida desde el día uno. Sin esto, en un año el histórico de desempeño no vale nada |
| 3 | **El ancla importa el error de otro.** Si Banrep se equivoca, el mapa se equivoca con él | Etiquetar el ancla y su fecha en la pieza. Publicar también la versión sin anclar, para que se vea el efecto del ancla |
| 4 | **La tentación de meter el IIF como regresor** para "conectar" con la tesis | Prohibido por ADR-019 (decisión 5). Contradice tu propio resultado publicado |
| 5 | **Los 15 departamentos pequeños son 7 % del PIB y el 100 % de la incertidumbre** | Es precisamente lo que la capa de confianza debe mostrar |
| 6 | **Un mapa de calor persuade más de lo que el modelo sostiene** | La regla del §4.3. Sin capa de incertidumbre, no se publica |
| 7 | Deuda: `pmdarima`, `arch` y `sktime` no están instalados | `statsmodels 0.15` alcanza para todo lo anterior. No añadas dependencias que no necesitas (R-02: solo `uv add`) |

---

## 8. Las dos decisiones que eran del autor - ya tomadas (23-sep-2026)

> **Horizonte: 2026-2028.** Fijado en ADR-019, con la medicion de cuanto aporta el ARIMA
> sobre la deriva a cada horizonte: +14,6 % a un anio, +23,6 % a dos, +13,3 % a tres,
> +5,3 % a cuatro y -1,5 % a cinco.
>
> **Ancla nacional: aceptada.** Registrada en ADR-019; la reconciliacion jerarquica se
> detalla en ADR-021.
>
> **Tablero macro auxiliar:** resuelto aparte, en el repositorio `macro-forecast-lab-latam`.

Texto original de la consulta:


1. **Horizonte.** 2026–2028 es lo que los datos aguantan con decencia. Más allá de tres años,
   un ARIMA con 20 observaciones converge a la deriva y el mapa deja de tener información.
   ¿Te sirven tres años, o el sitio necesita llegar a 2030 por razones de narrativa?

2. **El tablero macro auxiliar.** ¿Pieza de portafolio aparte, o te quedas con la capa de
   proyección dentro del proyecto de inclusión financiera? Mi recomendación es lo segundo
   primero, y lo primero después si quieres mostrar amplitud macro.

---

## Anexo — comandos de verificación usados en este plan

```bash
uv run python -m iif.forecast.backtest   # cuando el modulo exista
```

Las mediciones de este documento se hicieron con `statsmodels` sobre
`data/interim/dane/pib_departamento_anual.parquet`. Las definitivas, con prueba de
significancia y origen movil, estan en ADR-019, ADR-020, ADR-021 y ADR-022.

Cifras citadas y su origen:

- Cobertura, nulos, `estado_dato`: lectura directa de `pib_departamento_anual.parquet`
- Backtest §2: ajuste de 5 órdenes ARIMA × 2 (con/sin exógenas) + 3 benchmarks × 33 deptos
- Brechas jerárquicas §1.2: suma de 33 deptos vs fila `dpto_ccdgo == "00"`
- Pesos §1.3: participación en `pib_constante_2015_mm`, año 2023 (último definitivo)
- Crecimientos nacionales: log-diferencias ×100, **no** las tasas aritméticas publicadas por el
  DANE. Difieren en la segunda decimal
- Consenso EME 2026 (2,8 %): Banrep, resultados de mayo de 2026
