-- Dólar implícito no bitcoin, barras de 1h (início da barra em UTC), 24 h por dia:
-- USD/BRL = BTCBRL / BTCUSDT (Binance, mesma barra). Checagem cruzada com o BTC-USD do Yahoo.
with brl as (
    select data_hora_utc, fechamento, volume
    from {{ source('bruto', 'binance_horario') }}
    where par = 'BTCBRL' and fechamento > 0
),

usdt as (
    select data_hora_utc, fechamento
    from {{ source('bruto', 'binance_horario') }}
    where par = 'BTCUSDT' and fechamento > 0
),

btc_usd_yahoo as (
    select data_hora_utc, fechamento
    from {{ source('bruto', 'yahoo_horario') }}
    where ticker = 'BTC-USD' and fechamento > 0
)

select
    b.data_hora_utc,
    b.fechamento as btc_brl,
    u.fechamento as btc_usdt,
    b.fechamento / u.fechamento as dolar_implicito,
    b.fechamento / y.fechamento as dolar_implicito_yahoo,
    b.volume as volume_btc
from brl b
join usdt u using (data_hora_utc)
left join btc_usd_yahoo y using (data_hora_utc)
