# Licencias de los datos

Qué licencia tiene cada fuente, cómo se atribuye y qué implica para lo que este repositorio deriva de ella. La licencia de cada descarga concreta queda además en `data/raw/manifest.jsonl` (la columna `dim_vintage.licencia` que prevé ADR-002 todavía no existe). Decisión de fondo: ADR-012.

## Fuentes

### Superintendencia Financiera de Colombia (SFC), datos.gov.co

- Conjuntos: `ptgf-ywrb` (inclusión financiera por entidad y municipio, 2017Q4 a 2021Q1, congelado), `kx2f-xjdq` (mismo grano, 2021Q1 a 2025Q4, vigente), `vkbt-desu` (puntos de atención por entidad y municipio, mensual, 2023-01 en adelante).
- Licencia: Creative Commons Atribución-CompartirIgual 4.0 Internacional (CC BY-SA 4.0), según la ficha de cada conjunto en datos.gov.co.
- Atribución que se usa: "Contiene datos de la Superintendencia Financiera de Colombia publicados en datos.gov.co bajo CC BY-SA 4.0, conjunto <id>, descargado el <fecha> (`rowsUpdatedAt` <fecha de la fuente>), transformado por el proyecto financial-inclusion-colombia."
- Nota: los ceros fuera del bloque de producto de cada fila son relleno de la plataforma, no datos (ADR-008).

### DANE: PIB departamental, valor agregado municipal, población, ITAED, PIB trimestral de Bogotá, ISE, EMMET

- Acceso: archivos XLSX publicados en dane.gov.co.
- Licencia: información pública del Estado colombiano sin licencia Creative Commons explícita en los archivos. El DANE pide citar la fuente.
- Atribución que se usa: "Fuente: DANE, <nombre del archivo>, versión con `Last-Modified` <AAAA-MM-DD>, descargado el <fecha>. Cálculos propios." El nombre del archivo en `data/raw/dane/` lleva el sufijo `__lmAAAAMMDD` para que la cita sea exacta aunque el DANE republique la serie.
- Nota: el PIB departamental es base 2015 y toda la serie se revisa cada julio; el valor agregado municipal es una distribución del PIB departamental con indicadores; la población se toma siempre de las proyecciones `_VP`.

### Ministerio de Tecnologías de la Información y las Comunicaciones (MinTIC), datos.gov.co

- Conjunto: `n48w-gutb` (accesos a internet fijo por municipio, trimestral, 2016Q1 a 2023Q3, con cobertura sustantiva desde 2017Q2: 2016 trae 56 filas; abandonado en 2024).
- Licencia: CC BY-SA 4.0.
- Atribución que se usa: "Contiene datos de MinTIC publicados en datos.gov.co bajo CC BY-SA 4.0, conjunto n48w-gutb, descargado el <fecha>, transformado por el proyecto."
- Nota: decimales con coma; la ausencia de fila es no observado.

### Ministerio de Educación Nacional (MEN), datos.gov.co

- Conjunto: `nudc-7mev` (estadísticas de educación por municipio, anual, 2011 a 2024).
- Licencia: CC BY-SA 4.0.
- Atribución que se usa: "Contiene datos del Ministerio de Educación Nacional publicados en datos.gov.co bajo CC BY-SA 4.0, conjunto nudc-7mev, descargado el <fecha>, transformado por el proyecto."
- Nota: los ceros en tasas son faltantes (`nullif`); hay un quiebre metodológico en 2018.

### DANE: Marco Geoestadístico Nacional (MGN) 2024

- Acceso: servicio ArcGIS REST del DANE (`f=geojson`), capas de departamentos (33) y municipios (1.121) con códigos DIVIPOLA. La página de descarga oficial responde 404; el servicio no.
- Licencia: sin licencia explícita; información pública del DANE. Se atribuye.
- Atribución que se usa: "Límites: DANE, Marco Geoestadístico Nacional 2024, obtenido del servicio REST el <fecha>, simplificado para el atlas."

### Ancla nacional del pronóstico: Banrep, Encuesta mensual de expectativas de analistas económicos (EME)

- Uso: mediana, mínimo y máximo de las expectativas de crecimiento anual del PIB para 2026 y 2027 (seis cifras, total de la muestra), transcritas en `config/forecast.yaml` (ADR-021, adenda 1). Se convierten de fracción a por ciento sin redondear. El valor de 2028 no viene de la EME: es un supuesto del proyecto y la fuente lo dice. El escenario central queda en `data/processed/forecast/resultados.json` (`ancla`) y en el atlas.
- Acceso: portal de estadísticas de Banrep (suameca.banrep.gov.co), Encuestas, 1.1 EME. Archivo `res_inf_jul2026.xlsx`, hoja `PIB`, bloque «TODAS LAS ENTIDADES PARTICIPANTES». Consultado el 2026-09-25. El archivo no se redistribuye: la ficha metodológica pide que los resultados se obtengan por descarga directa de Banrep.
- Términos: aviso legal de Banrep, https://www.banrep.gov.co/es/aviso-legal (última modificación: 2026-06-03), leído el 2026-09-25. No hay términos propios de la EME: la ficha metodológica (2025) y la metodología no traen cláusula de licencia.
  - **§2.** La información económica de tipo estadístico puede reproducirse y divulgarse libremente, con tres condiciones: no alterar su contenido, indicar la fuente y mencionar la fecha en que se consultó el portal. Excluye «análisis, adaptaciones, proyecciones, compilaciones, comentarios u opiniones».
  - **§6.** El resto del contenido está protegido por derecho de autor. Se reproduce citando fuente, obra y autor, y sin fines comerciales o promocionales salvo autorización previa. El nombre y el logo del Banco son marcas: se nombra al Banco como fuente, sin usar su logo.
- Cómo se cumple (B-092):
  - La fuente publicada nombra la encuesta, la edición, el estadístico y la fecha de consulta, y dice que son expectativas de los analistas encuestados, no pronósticos del Banco.
  - El cambio de unidad no altera el valor.
  - 2028 se declara como supuesto propio.
  - Uso académico y no comercial.
- Duda abierta: la ficha describe la EME como una operación estadística que publica «estadísticas descriptivas», lo que la acerca a la §2. Pero lo que describe son expectativas, y la §2 excluye «proyecciones» y «compilaciones», así que el texto no cierra la cuestión. Si cae en la §6, publicarla en el portafolio personal del autor (davirson.com) queda en zona gris, porque «promocionales» no está definido. La confirmación escrita la puede dar el buzón de la EME que figura en su metodología: DTIE-EstadisticaEnc@banrep.gov.co.
- Atribución que se usa: "Banrep, Encuesta mensual de expectativas de analistas económicos (EME) de julio de 2026, mediana de los analistas, consultada el 2026-09-25 (2028 repite 2027, supuesto del proyecto)".

### Respaldo del ancla: FMI, World Economic Outlook Database (API SDMX del FMI)

- Uso: `src/iif/forecast/anchor.py` baja de `api.imf.org` la serie `COL.NGDP_RPCH.A` (una serie, tres años, una llamada por corrida) cuando `config/forecast.yaml` no trae ancla. La fecha de corte es el `PUBLICATION_DATE` del conjunto. Las cifras del WEO de abril de 2026 (2,34 / 2,54 / 2,62) se citan como contraste en ADR-021, adenda 1. Hasta el 2026-09-25 la serie se bajaba de DBnomics (B-091).
- Términos: «Copyright and Usage» del FMI, https://www.imf.org/en/about/copyright-and-terms (vigentes desde el 2024-10-11), leídos el 2026-09-25. El portal nuevo (data.imf.org, api.imf.org) no tiene términos propios y remite a estos.
  - **The Use of IMF Data.** Prevalece sobre la prohibición general de uso comercial y nombra expresamente la base del World Economic Outlook. Permite descargar, extraer, copiar, crear obras derivadas, publicar, distribuir y usar los datos con cuatro condiciones:
    - que aparezcan con exactitud y atribuidos al FMI; el ejemplo de cita es «Source: International Monetary Fund, Database Name, link»;
    - que una transformación material se declare junto a la cita;
    - promover esas condiciones entre quien reciba los datos;
    - avisar que son gratuitos si se venden.
  - Para cualquier reutilización comercial hay que pedir permiso (copyright@imf.org).
  - Siguen vigentes las condiciones generales: no descargar de forma masiva y automatizada sin permiso, no insinuar respaldo del FMI y no usar su sello ni su logo.
- Cómo se cumple (B-092):
  - Cuando el respaldo actúa, la fuente publicada es «Fondo Monetario Internacional, World Economic Outlook Database, <mes> de <año>, https://data.imf.org/en/datasets/IMF.RES:WEO, consultada el <fecha>».
  - El uso como ancla de una reconciliación es una transformación que ADR-021 declara.
  - Una sola serie por corrida.
  - Uso académico y no comercial.
  - Sin logo.

### Fuentes descartadas

DIAN (seccional no equivale a departamento), XM (operador de red, no unidad territorial), DNP TerriData (sin API y no accesible desde la sesión), RIF 2025 de Banca de las Oportunidades (sin anexo en Excel), GeoJSON de GitHub (sin licencia, 2018). No se usan y no hay que atribuirlas.

## Qué implica para lo derivado

- CompartirIgual se hereda. Cualquier tabla, Parquet, mart de dbt, exportación del atlas o gráfico del sitio que contenga datos de SFC, MinTIC o MEN se publica bajo CC BY-SA 4.0 (R-14). Esto incluye `data/legacy/panel_fintech_colombia_trimestral.*`, `data/raw/`, `data/interim/`, `data/processed/`, los marts y `atlas/data/`.
- Los derivados solo del DANE se publican también como CC BY-SA 4.0 para no tener dos regímenes en el mismo mart, con la atribución del DANE.
- Quien reutilice estos datos debe: atribuir a la fuente original y a este proyecto, enlazar la licencia, indicar si hizo cambios, y licenciar su derivado bajo CC BY-SA 4.0.
- El código (`src/`, `dbt/`, `scripts/`, `tests/`) es MIT y no se ve afectado: la licencia de los datos no contamina el código que los procesa.
- El texto del trabajo de grado y del manuscrito es del autor (ver README, sección Licencia).
- Una fuente con licencia más restrictiva que CC BY-SA 4.0 no entra a los marts sin un ADR nuevo.

## Texto corto para el sitio y el README

"Datos derivados: CC BY-SA 4.0. Contienen datos de la Superintendencia Financiera de Colombia, MinTIC y el Ministerio de Educación Nacional publicados en datos.gov.co bajo CC BY-SA 4.0, y datos públicos del DANE. Detalle por fuente y fecha en docs/LICENCIAS_DATOS.md y en data/raw/manifest.jsonl."
