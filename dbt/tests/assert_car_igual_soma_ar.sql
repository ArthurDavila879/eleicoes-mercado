-- O CAR da tabela de resultados é a soma dos retornos anormais da janela
with soma as (
    select frequencia, evento_id, ativo, sum(retorno_anormal) as soma_ar
    from {{ ref('fct_retornos_anormais') }}
    group by all
)
select c.*
from {{ ref('fct_car_eventos') }} c
join soma s using (frequencia, evento_id, ativo)
where abs(c.car - s.soma_ar) > 1e-12
