-- Volume diário negociado (Yahoo) dos ativos com volume (índice e ações; moedas vêm com 0)
select
    ticker as ativo,
    cast(data as date) as data,
    volume
from {{ source('bruto', 'yahoo_diario') }}
where volume > 0
  and ticker not like '%=X'
