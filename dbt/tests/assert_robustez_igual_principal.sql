-- A reimplementação em Python (src/estatistica) reproduz o estudo principal em SQL:
-- mesmos status, nº de observações, CAR, t e p-valor em todos os evento × ativo × frequência
select r.frequencia, r.evento_id, r.ativo
from {{ ref('resultados_eventos') }} r
join {{ ref('fct_testes_robustez') }} t using (frequencia, evento_id, ativo)
where (r.car is null) <> (t.car is null)
   or abs(r.car - t.car) > 1e-10
   or abs(r.estatistica_t - t.estatistica_t) > 1e-8
   or (r.p_valor is null) <> (t.p_valor is null)
   or abs(r.p_valor - t.p_valor) > 1e-10
   or (r.car is not null and (r.n_obs <> t.n_obs or r.status <> t.status))
union all
-- e a janela principal da sensibilidade é a própria análise principal
select 'diaria', s.evento_id, s.ativo
from {{ ref('fct_sensibilidade_janelas') }} s
join {{ ref('resultados_eventos') }} r
  on r.frequencia = 'diaria' and r.evento_id = s.evento_id and r.ativo = s.ativo
where s.principal
  and ((r.car is null) <> (s.car is null) or abs(r.car - s.car) > 1e-10
       or (r.p_valor is null) <> (s.p_valor is null) or abs(r.p_valor - s.p_valor) > 1e-10)
