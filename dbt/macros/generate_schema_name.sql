{# Usa o nome do schema configurado diretamente (staging, intermediario, marts),
   sem o prefixo do schema padrão do perfil. #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}{{ target.schema }}{%- else -%}{{ custom_schema_name | trim }}{%- endif -%}
{%- endmacro %}
