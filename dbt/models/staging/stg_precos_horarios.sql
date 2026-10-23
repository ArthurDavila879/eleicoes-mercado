-- Barras de 1h: preço de fechamento da barra que começa em data_hora_utc.
-- Carteiras long-short: razão P_long / P_short nas barras com os dois preços.
with barras as (
    select
        ticker as ativo,
        data_hora_utc,
        fechamento as preco
    from {{ source('bruto', 'yahoo_horario') }}
    where fechamento > 0
)

select * from barras
union all
select c.carteira as ativo, l.data_hora_utc, l.preco / s.preco as preco
from {{ ref('carteiras') }} c
join barras l on l.ativo = c.ativo_long
join barras s on s.ativo = c.ativo_short and s.data_hora_utc = l.data_hora_utc
