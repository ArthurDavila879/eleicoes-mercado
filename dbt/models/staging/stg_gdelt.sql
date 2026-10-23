-- Volume e tom diários por candidato. volume_relativo = artigos do dia / média do próprio
-- candidato no período (permite comparar a dinâmica sem comparar níveis entre nomes).
select
    candidato,
    cast(data as date) as data,
    consulta,
    n_artigos,
    total_monitorado,
    case when n_artigos > 0 then tom_medio end as tom_medio,  -- sem artigos, tom indefinido
    n_artigos / nullif(avg(n_artigos) over (partition by candidato), 0) as volume_relativo
from {{ source('bruto', 'gdelt_diario') }}
