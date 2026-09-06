# ADR-012 · Datos derivados bajo CC BY-SA 4.0

- Fecha: 2026-09-06
- Estado: aceptada

## Contexto

Las tablas de la Superintendencia Financiera en datos.gov.co (`ptgf-ywrb`, `kx2f-xjdq`, `vkbt-desu`), la de MinTIC (`n48w-gutb`) y la del MEN (`nudc-7mev`) se publican bajo Creative Commons Atribución-CompartirIgual 4.0 (CC BY-SA 4.0). CompartirIgual obliga a licenciar las obras derivadas bajo la misma licencia. Los datos del DANE son públicos sin licencia CC explícita. El código del repo es MIT y el texto de la tesis es del autor.

## Decisión

1. Todo dato derivado que contenga datos de SFC, MinTIC o MEN (Parquet de `data/raw/`, `data/interim/`, `data/processed/`, marts de dbt, exportaciones del atlas en `atlas/data/`, y las tablas del sitio) se publica bajo CC BY-SA 4.0.
2. La atribución se escribe en `docs/LICENCIAS_DATOS.md`, en el manifiesto (`licencia` por descarga) y en `dim_vintage.licencia`.
3. Los datos derivados solo del DANE llevan la atribución del DANE y el archivo y `Last-Modified` de origen; se publican también como CC BY-SA 4.0 para no tener dos regímenes en el mismo mart.
4. El código sigue MIT. El texto del manuscrito y de la tesis, derechos del autor hasta el depósito.
5. El panel legado de la tesis (`data/legacy/`) deriva de SFC, DANE, MinTIC y MEN; queda bajo CC BY-SA 4.0 con la misma nota.

## Alternativas consideradas

- CC BY 4.0 para todo: incompatible con CompartirIgual de las fuentes.
- No declarar licencia de datos: deja al lector sin saber qué puede hacer y no cumple la atribución exigida.
- Separar marts por licencia: complica el modelo y no aporta nada al lector.

## Consecuencias

- Cualquier reutilización de los marts o del atlas debe atribuir y compartir igual (R-14).
- El README y el sitio muestran la licencia de datos junto a la de código.
- Un dato de una fuente con licencia más restrictiva no puede entrar a los marts sin ADR nuevo.

## Cómo revertirla

Solo si las fuentes cambian de licencia. Entonces un ADR nuevo actualiza `LICENCIAS_DATOS.md`, el manifiesto y `dim_vintage`.
