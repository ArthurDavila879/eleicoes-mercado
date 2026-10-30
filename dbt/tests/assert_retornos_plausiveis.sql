-- Log-retornos finitos e sem saltos absurdos (|r| > 0,7 em log, ≈ +100% ou −50%, indica erro
-- de dado) nos ativos que entram nos modelos (analisados, moedas de controle e mercado global).
-- O limite era 0,5 até a coleta recuar a 2014: a PRIO3 subiu 61% em log em 24/03/2016 (real).
-- Fatores globais e cripto ficam de fora: o VIX, por exemplo, tem altas reais de 77% num dia.
-- Exceções verificadas (movimento real, não erro de dado), uma linha por ativo e data:
--   MGLU3.SA 26/10/2026: −58,23% (log −0,87) no 1º pregão após o 2º turno, sem desdobramento
--   nem outro evento corporativo (InfoMoney, 26/10/2026: "Magalu, Azzas, C&A: ações de varejo
--   caem até 58% após reeleição de Lula").
with excecoes as (
    select * from (values ('MGLU3.SA', date '2026-10-26')) as e(ativo, dia)
),

usados as (
    select ativo from {{ ref('ativos') }} where classe not in ('fator_global', 'cripto')
    union all
    select carteira from {{ ref('carteiras') }}
)
select * from {{ ref('int_retornos_diarios') }} r
where ativo in (select ativo from usados)
  and not exists (select 1 from excecoes e where e.ativo = r.ativo and e.dia = cast(r.tempo as date))
  and log_retorno is not null and (isinf(log_retorno) or isnan(log_retorno) or abs(log_retorno) > 0.7)
union all
select * from {{ ref('int_retornos_horarios') }}
where ativo in (select ativo from usados)
  and log_retorno is not null and (isinf(log_retorno) or isnan(log_retorno) or abs(log_retorno) > 0.7)
