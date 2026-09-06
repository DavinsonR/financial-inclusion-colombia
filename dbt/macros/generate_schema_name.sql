{#-
  Esquemas con nombre limpio: `staging`, `intermediate`, `marts`, `seeds` en vez de
  `main_staging`, ... Así el DuckDB local y la base IIF de Snowflake (raw/staging/marts)
  comparten nomenclatura. Sin esquema personalizado se usa el del perfil.
-#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
