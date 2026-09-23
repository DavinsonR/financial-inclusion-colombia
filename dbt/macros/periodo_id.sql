{#-
  Clave natural de dim_periodo a partir de una fecha: A -> 'YYYY', Q -> 'YYYYQn', M -> 'YYYY-MM'.
  Solo usa extract() y lpad(), comunes a DuckDB, Snowflake y BigQuery; el texto sale de dbt.type_string().
-#}
{% macro periodo_id(date_col, freq) -%}
    {%- set anio = "cast(extract(year from " ~ date_col ~ ") as " ~ dbt.type_string() ~ ")" -%}
    {%- if freq == 'A' -%}
        {{ anio }}
    {%- elif freq == 'Q' -%}
        {{ anio }} || 'Q' || cast(extract(quarter from {{ date_col }}) as {{ dbt.type_string() }})
    {%- elif freq == 'M' -%}
        {{ anio }} || '-' || lpad(cast(extract(month from {{ date_col }}) as {{ dbt.type_string() }}), 2, '0')
    {%- else -%}
        {{ exceptions.raise_compiler_error("periodo_id: frecuencia desconocida '" ~ freq ~ "' (usar A, Q o M)") }}
    {%- endif -%}
{%- endmacro %}
