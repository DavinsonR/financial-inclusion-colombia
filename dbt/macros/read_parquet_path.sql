{#-
  Lee un Parquet del repositorio por ruta relativa a la raíz (IIF_ROOT). Solo tiene sentido en DuckDB.
  En BigQuery los Parquet se cargan antes con `bash bigquery/01_load_parquet.sh` y en Snowflake con
  stage interno + COPY INTO; en ambos los modelos leen de source(), por eso aquí se falla en compilación.
  dbt cambia el cwd a dbt/, de ahí que el valor por defecto de IIF_ROOT sea '..'.
-#}
{% macro read_parquet_path(relative) -%}
    {%- if target.type == 'duckdb' -%}
        read_parquet('{{ env_var("IIF_ROOT", "..") }}/{{ relative }}')
    {%- else -%}
        {{ exceptions.raise_compiler_error(
            "read_parquet_path('" ~ relative ~ "') solo está disponible con target.type = duckdb; en "
            ~ target.type ~ " cargue el Parquet vía stage + COPY INTO y use source()."
        ) }}
    {%- endif -%}
{%- endmacro %}
