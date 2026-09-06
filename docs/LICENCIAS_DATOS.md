# Licencias de los datos

Qué licencia tiene cada fuente, cómo se atribuye y qué implica para lo que este repositorio deriva de ella. La licencia de cada descarga concreta queda además en `data/raw/manifest.jsonl` y en `dim_vintage.licencia`. Decisión de fondo: ADR-012.

## Fuentes

### Superintendencia Financiera de Colombia (SFC), datos.gov.co

- Conjuntos: `ptgf-ywrb` (inclusión financiera por entidad y municipio, 2017Q4 a 2021Q1, congelado), `kx2f-xjdq` (mismo grano, 2021Q1 a 2025Q4, vigente), `vkbt-desu` (puntos de atención por entidad y municipio, mensual, 2023-01 en adelante).
- Licencia: Creative Commons Atribución-CompartirIgual 4.0 Internacional (CC BY-SA 4.0), según la ficha de cada conjunto en datos.gov.co.
- Atribución que se usa: "Contiene datos de la Superintendencia Financiera de Colombia publicados en datos.gov.co bajo CC BY-SA 4.0, conjunto <id>, descargado el <fecha> (`rowsUpdatedAt` <fecha de la fuente>), transformado por el proyecto inclusion-financiera-colombia."
- Nota: los ceros fuera del bloque de producto de cada fila son relleno de la plataforma, no datos (ADR-008).

### DANE: PIB departamental, valor agregado municipal, población, ITAED, PIB trimestral de Bogotá, ISE, EMMET

- Acceso: archivos XLSX publicados en dane.gov.co.
- Licencia: información pública del Estado colombiano sin licencia Creative Commons explícita en los archivos. El DANE pide citar la fuente.
- Atribución que se usa: "Fuente: DANE, <nombre del archivo>, versión con `Last-Modified` <AAAA-MM-DD>, descargado el <fecha>. Cálculos propios." El nombre del archivo en `data/raw/dane/` lleva el sufijo `__lmAAAAMMDD` para que la cita sea exacta aunque el DANE republique la serie.
- Nota: el PIB departamental es base 2015 y toda la serie se revisa cada julio; el valor agregado municipal es una distribución del PIB departamental con indicadores; la población se toma siempre de las proyecciones `_VP`.

### Ministerio de Tecnologías de la Información y las Comunicaciones (MinTIC), datos.gov.co

- Conjunto: `n48w-gutb` (accesos a internet fijo por municipio, trimestral, 2017Q2 a 2023Q3; abandonado en 2024).
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
