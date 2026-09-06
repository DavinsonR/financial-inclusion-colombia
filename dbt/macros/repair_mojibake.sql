{#-
  Repara las cadenas mal decodificadas que traen los datos de la SFC:
  - UTF-8 leído como CP1252/Latin-1 ("Ã¡" -> "á", "Ã±" -> "ñ", "Ã" + U+00AD -> "í", ...).
  - Latin-1 leído como Shift-JIS: katakana de media anchura "ﾑ" (U+FF91) -> "Ñ", "ﾓ" (U+FF93) -> "Ó"
    (así llega "NARIﾑO" en ptgf-ywrb).
  Los pares se escriben con chr() por punto de código para que ningún carácter invisible
  (guion suave U+00AD, controles C1) viva en el código fuente. chr() existe en DuckDB y en Snowflake.
  Casos de referencia: tests/assert_macros_texto_casos_conocidos.sql.
-#}
{% macro repair_mojibake(col) -%}
    {%- set pares = [
        ([195, 161], 'á'), ([195, 169], 'é'), ([195, 173], 'í'), ([195, 179], 'ó'), ([195, 186], 'ú'),
        ([195, 177], 'ñ'), ([195, 188], 'ü'),
        ([195, 8216], 'Ñ'), ([195, 145], 'Ñ'),
        ([195, 129], 'Á'), ([195, 8240], 'É'), ([195, 137], 'É'), ([195, 141], 'Í'),
        ([195, 8220], 'Ó'), ([195, 147], 'Ó'), ([195, 353], 'Ú'), ([195, 154], 'Ú'),
        ([65425], 'Ñ'), ([65427], 'Ó')
    ] -%}
    {%- set ns = namespace(expr=col) -%}
    {%- for cps, bueno in pares -%}
        {%- set partes = [] -%}
        {%- for cp in cps -%}
            {%- do partes.append('chr(' ~ cp ~ ')') -%}
        {%- endfor -%}
        {%- set ns.expr = 'replace(' ~ ns.expr ~ ', ' ~ (partes | join(' || ')) ~ ", '" ~ bueno ~ "')" -%}
    {%- endfor -%}
    {{ ns.expr }}
{%- endmacro %}
