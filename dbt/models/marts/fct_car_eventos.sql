-- CAR por evento × ativo × frequência e estatística t.
-- Var(CAR) = L · sigma2 (L = nº de retornos anormais na janela), supondo AR independentes
-- e ignorando o erro de estimação dos parâmetros (aproximação usual em estudos de evento).
-- Inclui todos os pares evento × ativo, inclusive os ainda sem dados (ver coluna status).
{% set n_diario = var('janela_diaria_fim') - var('janela_diaria_inicio') + 1 %}
{% set n_horario = var('janela_horaria_fim') - var('janela_horaria_inicio') + 1 %}
{% set rotulo_diario = '[' ~ var('janela_diaria_inicio') ~ ',+' ~ var('janela_diaria_fim') ~ '] pregões' %}
{% set rotulo_horario = '[' ~ var('janela_horaria_inicio') ~ 'h,+' ~ (var('janela_horaria_fim') + 1) ~ 'h]' %}

with combinacoes as (
    select
        f.frequencia,
        e.evento_id,
        a.ativo,
        case f.frequencia when 'diaria' then {{ n_diario }} else {{ n_horario }} end as n_esperado,
        case f.frequencia
            when 'diaria' then {{ var('min_obs_estimacao_diaria') }}
            else {{ var('min_obs_estimacao_horaria') }}
        end as min_estimacao,
        case f.frequencia when 'diaria' then '{{ rotulo_diario }}' else '{{ rotulo_horario }}' end
            as janela
    from (values ('diaria'), ('horaria')) as f(frequencia)
    cross join {{ ref('stg_eventos') }} e
    cross join {{ ref('ativos') }} a
    where a.modelo_retorno_normal <> 'nenhum'
      -- o dólar do BCB/SGS é diário: não entra na análise horária
      and not (f.frequencia = 'horaria' and a.ativo = 'BCB_DOLAR')
      -- eleições anteriores (2014–2022): só diária, não há barras de 1h dessa época
      and not (f.frequencia = 'horaria'
               and e.data_hora_utc < cast('{{ var("inicio_analise_horaria") }}' as timestamp))
),

agregado as (
    select
        frequencia,
        evento_id,
        ativo,
        count(*) as n_obs,
        sum(retorno_anormal) as car,
        min(tempo) as inicio_janela,
        max(tempo) as fim_janela
    from {{ ref('fct_retornos_anormais') }}
    group by all
)

select
    c.frequencia,
    c.janela,
    c.evento_id,
    c.ativo,
    p.modelo_retorno_normal,
    coalesce(a.n_obs, 0) as n_obs,
    c.n_esperado,
    a.inicio_janela,
    a.fim_janela,
    a.car,
    p.alfa,
    p.beta,
    p.n_estimacao,
    p.graus_liberdade,
    sqrt(p.sigma2) as sigma,
    sqrt(a.n_obs * p.sigma2) as erro_padrao_car,
    a.car / nullif(sqrt(a.n_obs * p.sigma2), 0) as estatistica_t,
    case
        when coalesce(a.n_obs, 0) = 0 and p.n_estimacao is null then 'aguardando_dados'
        when p.n_estimacao is null or p.n_estimacao < c.min_estimacao then 'estimacao_insuficiente'
        when coalesce(a.n_obs, 0) = 0 then 'aguardando_dados'
        when a.n_obs < c.n_esperado then 'janela_parcial'
        else 'completo'
    end as status
from combinacoes c
left join agregado a using (frequencia, evento_id, ativo)
left join {{ ref('fct_parametros_modelo') }} p using (frequencia, evento_id, ativo)
