-- p-valores dos testes de robustez entre 0 e 1; o empírico nunca abaixo de 1/(n+1);
-- Holm nunca menor que o p-valor original
select frequencia, evento_id, ativo, 'testes' as origem
from {{ ref('fct_testes_robustez') }}
where p_patell not between 0 and 1 or p_bmp not between 0 and 1
   or p_corrado not between 0 and 1 or p_valor_holm not between 0 and 1
   or p_valor_holm < p_valor - 1e-12
union all
select frequencia, evento_id, ativo, 'placebo'
from {{ ref('fct_placebo_resultados') }}
where p_empirico not between 0 and 1 or p_empirico < 1.0 / (n_placebo + 1) - 1e-12
union all
select 'diaria', evento_id, ativo, 'sensibilidade'
from {{ ref('fct_sensibilidade_janelas') }}
where p_valor not between 0 and 1
