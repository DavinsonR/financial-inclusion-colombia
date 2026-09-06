# ADR-003 · Parquet en el repo por debajo de 45 MB, Releases como desborde, DVC diferido

- Fecha: 2026-09-06
- Estado: aceptada

## Contexto

Las fuentes verificadas suman millones de filas: SFC `kx2f` 1,75 millones (99 columnas), `vkbt` 1,73 millones, MinTIC 2,8 millones. GitHub rechaza archivos de más de 100 MB y avisa desde 50 MB. Desde la sesión del asistente no se pueden subir Release assets (`gh` ausente, API bloqueada; B-023). El autor quiere que el repo se clone y corra sin pasos externos.

## Decisión

1. Los datos crudos se guardan como Parquet particionado por año (`data/raw/<fuente>/<dataset>/anio=YYYY/part-0.parquet`) y los XLSX del DANE con sufijo `__lmYYYYMMDD`.
2. Puerta de tamaño: 45 MB por archivo (`max_file_mb` en `config/sources.yaml`). Lo que la supere va a `data/raw/_large/` (ignorado por git), con entrada en la bitácora y en el manifiesto.
3. Los archivos de `_large/` los sube el autor como Release assets desde el navegador; `iif acquire` sabe descargarlos de la Release cuando faltan.
4. Tope orientativo del repo en git: 150 MB de datos.
5. DVC se difiere. Se reconsidera si el desborde supera cinco archivos o si aparece un colaborador.
6. Todo archivo de `data/raw/` tiene una fila en `data/raw/manifest.jsonl` (sha256, filas, bytes, URL, fechas, licencia). `iif manifest verify` comprueba que el disco coincide con el manifiesto.

## Alternativas consideradas

- Git LFS: cuota gratuita de 1 GB y ancho de banda limitado; los clones se vuelven lentos y las descargas de LFS cuentan contra la cuota.
- DVC con remoto en S3 o Drive: correcto para equipos; para una persona añade una cuenta, credenciales y un remoto que mantener.
- Todo fuera del repo: obliga a un paso manual antes de correr cualquier cosa y rompe CI.

## Consecuencias

- El repo se clona y `make check` corre sin datos externos gracias al panel legado y a las particiones pequeñas.
- Las particiones grandes exigen la acción del autor una vez por descarga.
- Los Parquet derivados de SFC, MinTIC y MEN heredan CC BY-SA 4.0 (ADR-012).

## Cómo revertirla

Adoptar DVC: `dvc init`, mover `data/raw/` a `.dvc`, elegir remoto, y cambiar `iif acquire` para que registre en DVC en vez de en git. El manifiesto se conserva igual.
