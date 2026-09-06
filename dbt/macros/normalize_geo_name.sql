{#-
  Clave de comparación para nombres geográficos: mayúsculas, sin acentos, puntuación -> espacio,
  espacios colapsados y recortados. "Bogotá, D.C." y "Bogota D.C." -> "BOGOTA D C";
  "San Andres,Prov Y Santa Catalina" -> "SAN ANDRES PROV Y SANTA CATALINA".
  No repara mojibake: encadenar repair_mojibake() antes cuando la fuente lo necesite.
  regexp_replace difiere de dialecto: DuckDB exige la bandera 'g'; Snowflake reemplaza todo por defecto.
-#}
{% macro normalize_geo_name(col) -%}
    {%- set sin_acentos = "translate(upper(" ~ col ~ "), 'ÁÉÍÓÚÜÑÀÈÌÒÙÂÊÎÔÛ', 'AEIOUUNAEIOUAEIOU')" -%}
    {%- if target.type == 'duckdb' -%}
        trim(regexp_replace(regexp_replace({{ sin_acentos }}, '[^A-Z0-9]+', ' ', 'g'), ' +', ' ', 'g'))
    {%- else -%}
        trim(regexp_replace(regexp_replace({{ sin_acentos }}, '[^A-Z0-9]+', ' '), ' +', ' '))
    {%- endif -%}
{%- endmacro %}
