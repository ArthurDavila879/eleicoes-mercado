-- Eventos anteriores a inicio_analise_horaria (eleições de 2014–2022) só têm análise diária
select r.*
from {{ ref('resultados_eventos') }} r
join {{ ref('stg_eventos') }} e using (evento_id)
where r.frequencia = 'horaria'
  and e.data_hora_utc < cast('{{ var("inicio_analise_horaria") }}' as timestamp)
