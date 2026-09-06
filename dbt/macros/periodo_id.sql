{#-
  Clave natural de dim_periodo a partir de una fecha: A -> 'YYYY', Q -> 'YYYYQn', M -> 'YYYY-MM'.
  Solo usa extract() y lpad(), comunes a DuckDB y Snowflake.
-#}
{% macro periodo_id(date_col, freq) -%}
    {%- set anio = "cast(extract(year from " ~ date_col ~ ") as varchar)" -%}
    {%- if freq == 'A' -%}
        {{ anio }}
    {%- elif freq == 'Q' -%}
        {{ anio }} || 'Q' || cast(extract(quarter from {{ date_col }}) as varchar)
    {%- elif freq == 'M' -%}
        {{ anio }} || '-' || lpad(cast(extract(month from {{ date_col }}) as varchar), 2, '0')
    {%- else -%}
        {{ exceptions.raise_compiler_error("periodo_id: frecuencia desconocida '" ~ freq ~ "' (usar A, Q o M)") }}
    {%- endif -%}
{%- endmacro %}
