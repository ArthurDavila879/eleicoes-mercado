{# Falha para cada grupo (série, ticker, candidato) cujo último dado tem mais de
   max_dias_uteis dias úteis de atraso: conta os dias de segunda a sexta entre a data do
   último dado e hoje (exclusive nas duas pontas; o dia de hoje ainda pode estar em coleta).
   "Hoje" é a data em America/Sao_Paulo, ou var('data_referencia_atualizacao') nos testes.
   Feriados não são descontados (um feriado na semana pode gerar um alarme a mais).
   converter_fuso: true para colunas em UTC com hora (barras de 1h). #}
{% test atualizado_em_dias_uteis(model, column_name, grupo, max_dias_uteis=2, converter_fuso=false) %}
{% set data_referencia = var('data_referencia_atualizacao', none) %}
with hoje as (
    select
        {% if data_referencia %}
        cast('{{ data_referencia }}' as date)
        {% else %}
        cast(timezone('UTC', now()) + interval ({{ var('fuso_offset_horas') }}) hour as date)
        {% endif %} as d
),

ultimos as (
    select
        {{ grupo }} as grupo,
        {% if converter_fuso %}
        cast(max({{ column_name }}) + interval ({{ var('fuso_offset_horas') }}) hour as date)
        {% else %}
        cast(max({{ column_name }}) as date)
        {% endif %} as ultimo
    from {{ model }}
    group by 1
),

atraso as (
    select
        u.grupo,
        u.ultimo,
        h.d as hoje,
        (
            select count(*)
            from generate_series(cast(u.ultimo as timestamp) + interval 1 day,
                                 cast(h.d as timestamp) - interval 1 day, interval 1 day) as s(dia)
            where isodow(s.dia) <= 5
        ) as dias_uteis_sem_dado
    from ultimos u
    cross join hoje h
)

select *
from atraso
where dias_uteis_sem_dado > {{ max_dias_uteis }}
{% endtest %}
