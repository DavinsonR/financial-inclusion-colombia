{#-
  Lee un Parquet del repositorio por ruta relativa a la raíz (IIF_ROOT). Solo tiene sentido en DuckDB:
  en Snowflake los Parquet entran por stage interno + COPY INTO (snowflake/02_database_stages_copy.sql)
  y los modelos deben leer de source() en el esquema raw, por eso aquí se falla en compilación.
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
