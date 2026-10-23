{# Macros compartilhadas pelas frequências diária e horária do estudo de evento. #}

{# Log-retornos por ativo, na sequência das observações do próprio ativo.
   idx = posição da observação (pregão ou barra) na série do ativo. #}
{% macro log_retornos(modelo_precos, col_tempo) %}
select
    ativo,
    {{ col_tempo }} as tempo,
    preco,
    ln(preco / lag(preco) over w) as log_retorno,
    row_number() over w as idx
from {{ ref(modelo_precos) }}
window w as (partition by ativo order by {{ col_tempo }})
{% endmacro %}


{# Junta a cada retorno o retorno de referência exigido pelo modelo do ativo:
   - mercado: retorno do Ibovespa no mesmo pregão/barra (modelo de mercado);
   - mercado_global: retorno do ETF de emergentes (var ativo_mercado_global) entre os
     MESMOS dois pregões do ativo (ASOF: último fechamento do ETF até cada data), para que
     feriados só de um dos países não desalinhem os retornos. Só existe na análise diária;
     na horária o ativo cai para média constante (barras dos EUA começam na meia hora);
   - controle_moedas: média das moedas de controle no mesmo dia/hora;
   - media_constante / nenhum: sem referência. #}
{% macro retornos_com_referencia(modelo_retornos, frequencia) %}
with retornos as (
    select * from {{ ref(modelo_retornos) }}
    where log_retorno is not null
),

ativos as (
    select * from {{ ref('ativos') }}
),

mercado as (
    select tempo, log_retorno as r_mercado
    from retornos
    where ativo = '^BVSP'
),

controle as (
    select
        tempo,
        avg(log_retorno) as r_controle,
        count(*) as n_moedas_controle
    from retornos
    where ativo in (select ativo from ativos where classe = 'moeda_controle')
    group by tempo
    having count(*) >= {{ var('min_moedas_controle') }}
),

{% if frequencia == 'diaria' %}
precos_global as (
    select tempo, preco
    from {{ ref(modelo_retornos) }}
    where ativo = '{{ var("ativo_mercado_global") }}'
),

datas_ativo as (
    select ativo, tempo, lag(tempo) over (partition by ativo order by tempo) as tempo_anterior
    from {{ ref(modelo_retornos) }}
    where ativo in (select ativo from ativos where modelo_retorno_normal = 'mercado_global')
),

-- Só até o último fechamento coletado do ETF (senão o ASOF repetiria o preço e daria retorno 0)
global as (
    select d.ativo, d.tempo, ln(g1.preco / g0.preco) as r_global
    from datas_ativo d
    asof join precos_global g1 on d.tempo >= g1.tempo
    asof join precos_global g0 on d.tempo_anterior >= g0.tempo
    where d.tempo <= (select max(tempo) from precos_global)
),
{% endif %}

modelo_efetivo as (
    select
        ativo,
        classe,
        case
            when modelo_retorno_normal = 'mercado_global' and '{{ frequencia }}' <> 'diaria'
                then 'media_constante'
            else modelo_retorno_normal
        end as modelo_retorno_normal
    from ativos
)

select
    r.ativo,
    r.tempo,
    r.idx,
    r.log_retorno,
    a.classe,
    a.modelo_retorno_normal,
    m.r_mercado,
    c.r_controle,
    c.n_moedas_controle,
    case a.modelo_retorno_normal
        when 'mercado' then m.r_mercado
        {% if frequencia == 'diaria' %}when 'mercado_global' then g.r_global{% endif %}
        when 'controle_moedas' then c.r_controle
    end as r_referencia
from retornos r
join modelo_efetivo a on a.ativo = r.ativo
left join mercado m on m.tempo = r.tempo
left join controle c on c.tempo = r.tempo
{% if frequencia == 'diaria' %}left join global g on g.ativo = r.ativo and g.tempo = r.tempo{% endif %}
{% endmacro %}


{# Posiciona cada observação em relação a cada evento (rel = idx - idx do dia/barra 0)
   e marca a fase: 'estimacao' ou 'evento'. Observações da janela de estimação que caem
   na janela de OUTRO evento são descartadas (evita contaminar o modelo).
   inicio_evento: expressão SQL do primeiro instante que conta como dia/barra 0. #}
{% macro janelas_evento(modelo_ref, inicio_evento, est_ini, est_fim, jan_ini, jan_fim) %}
with obs as (
    select * from {{ ref(modelo_ref) }}
),

eventos as (
    select *, {{ inicio_evento }} as inicio_evento
    from {{ ref('stg_eventos') }}
),

-- Dia/barra 0: primeira observação do ativo a partir do início do evento
zero as (
    select e.evento_id, o.ativo, min(o.idx) as idx0
    from eventos e
    join obs o on o.tempo >= e.inicio_evento
    group by e.evento_id, o.ativo
),

relativas as (
    select
        z.evento_id,
        o.*,
        o.idx - z.idx0 as rel,
        case
            when o.idx - z.idx0 between {{ jan_ini }} and {{ jan_fim }} then 'evento'
            when o.idx - z.idx0 between {{ est_ini }} and {{ est_fim }} then 'estimacao'
        end as fase
    from zero z
    join obs o
      on o.ativo = z.ativo
     and o.idx - z.idx0 between {{ est_ini }} and {{ jan_fim }}
),

em_janela_de_evento as (
    select distinct evento_id, ativo, idx
    from relativas
    where fase = 'evento'
)

select r.*
from relativas r
where r.fase is not null
  and not (
      r.fase = 'estimacao'
      and exists (
          select 1 from em_janela_de_evento j
          where j.ativo = r.ativo and j.idx = r.idx and j.evento_id <> r.evento_id
      )
  )
{% endmacro %}


{# Parâmetros do retorno normal estimados na janela de estimação de cada evento×ativo.
   - mercado:          R = alfa + beta·R_ibov + e   (MQO; gl = n - 2)
   - mercado_global:   R = alfa + beta·R_EEM + e    (MQO; gl = n - 2)
   - media_constante:  R = alfa + e                  (gl = n - 1)
   - controle_moedas:  AR = R - média(controles); alfa = 0, beta = 1 (gl = n - 1)
   sigma2 = variância dos resíduos/retornos anormais na estimação. #}
{% macro parametros_modelo(modelo_janelas, frequencia) %}
with est as (
    select * from {{ ref(modelo_janelas) }}
    where fase = 'estimacao'
      and modelo_retorno_normal in ('mercado', 'mercado_global', 'media_constante', 'controle_moedas')
      and log_retorno is not null
      and (modelo_retorno_normal = 'media_constante' or r_referencia is not null)
),

coef as (
    select
        evento_id,
        ativo,
        any_value(modelo_retorno_normal) as modelo_retorno_normal,
        case
            when any_value(modelo_retorno_normal) in ('mercado', 'mercado_global')
                then regr_intercept(log_retorno, r_referencia)
            when any_value(modelo_retorno_normal) = 'media_constante' then avg(log_retorno)
            else 0
        end as alfa,
        case
            when any_value(modelo_retorno_normal) in ('mercado', 'mercado_global')
                then regr_slope(log_retorno, r_referencia)
            when any_value(modelo_retorno_normal) = 'media_constante' then 0
            else 1
        end as beta,
        count(*) as n_estimacao
    from est
    group by evento_id, ativo
),

residuos as (
    select
        e.evento_id,
        e.ativo,
        e.log_retorno - (c.alfa + c.beta * coalesce(e.r_referencia, 0)) as residuo
    from est e
    join coef c using (evento_id, ativo)
),

dispersao as (
    select
        evento_id,
        ativo,
        sum(residuo * residuo) as soma_quadrados,
        var_samp(residuo) as variancia_amostral
    from residuos
    group by evento_id, ativo
)

select
    '{{ frequencia }}' as frequencia,
    c.evento_id,
    c.ativo,
    c.modelo_retorno_normal,
    c.alfa,
    c.beta,
    c.n_estimacao,
    case when c.modelo_retorno_normal in ('mercado', 'mercado_global') then c.n_estimacao - 2 else c.n_estimacao - 1 end
        as graus_liberdade,
    -- mercado: soma dos quadrados dos resíduos / (n - 2); demais: variância amostral
    case
        when c.modelo_retorno_normal in ('mercado', 'mercado_global')
            then d.soma_quadrados / nullif(c.n_estimacao - 2, 0)
        else d.variancia_amostral
    end as sigma2
from coef c
join dispersao d using (evento_id, ativo)
{% endmacro %}


{# Retornos anormais na janela do evento (AR = retorno observado - retorno normal). #}
{% macro retornos_anormais(modelo_janelas, frequencia) %}
select
    '{{ frequencia }}' as frequencia,
    j.evento_id,
    j.ativo,
    j.rel,
    cast(j.tempo as timestamp) as tempo,
    j.log_retorno,
    j.r_referencia,
    p.alfa + p.beta * coalesce(j.r_referencia, 0) as retorno_normal,
    j.log_retorno - (p.alfa + p.beta * coalesce(j.r_referencia, 0)) as retorno_anormal
from {{ ref(modelo_janelas) }} j
join {{ ref('fct_parametros_modelo') }} p
  on p.evento_id = j.evento_id
 and p.ativo = j.ativo
 and p.frequencia = '{{ frequencia }}'
where j.fase = 'evento'
  and j.log_retorno is not null
  and (p.modelo_retorno_normal = 'media_constante' or j.r_referencia is not null)
{% endmacro %}
