-- Barras de 1h: preço de fechamento da barra que começa em data_hora_utc.
select
    ticker as ativo,
    data_hora_utc,
    fechamento as preco
from {{ source('bruto', 'yahoo_horario') }}
where fechamento > 0
