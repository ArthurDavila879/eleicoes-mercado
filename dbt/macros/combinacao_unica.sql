{# Teste genérico: a combinação das colunas informadas é única no modelo. #}
{% test combinacao_unica(model, colunas) %}
select {{ colunas | join(', ') }}, count(*) as n
from {{ model }}
group by {{ colunas | join(', ') }}
having count(*) > 1
{% endtest %}
