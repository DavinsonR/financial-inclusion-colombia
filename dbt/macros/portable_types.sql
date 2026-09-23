{#-
  Tipos y agregados que cambian de nombre entre DuckDB, Snowflake y BigQuery.
  - Texto: se usa dbt.type_string() (TEXT en DuckDB y Snowflake, STRING en BigQuery). BigQuery no acepta
    `varchar`, por eso ningún modelo escribe `cast(... as varchar)` a mano.
  - Doble precisión: `double` en DuckDB y Snowflake, `float64` en BigQuery. No se usa dbt.type_float()
    porque en DuckDB se traduce a FLOAT, que es de precisión simple (REAL) y perdería dígitos.
  - Mediana: `median()` existe en DuckDB y Snowflake; BigQuery solo tiene cuantiles aproximados como
    agregado, así que allí se usa APPROX_QUANTILES (suficiente para las pruebas de tolerancia que la usan).
-#}
{% macro type_double() -%}
    {%- if target.type == 'bigquery' -%} float64 {%- else -%} double {%- endif -%}
{%- endmacro %}

{% macro median_agg(expr) -%}
    {%- if target.type == 'bigquery' -%}
        approx_quantiles({{ expr }}, 2)[offset(1)]
    {%- else -%}
        median({{ expr }})
    {%- endif -%}
{%- endmacro %}
