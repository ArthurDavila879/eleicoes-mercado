-- Eventos com horário em UTC e no fuso de referência (America/Sao_Paulo = UTC-3).
select
    evento_id,
    tipo,
    descricao,
    fonte_url,
    data_hora_utc,
    data_hora_utc + interval ({{ var('fuso_offset_horas') }}) hour as data_hora_local,
    cast(data_hora_utc + interval ({{ var('fuso_offset_horas') }}) hour as date) as data_local,
    hour(data_hora_utc + interval ({{ var('fuso_offset_horas') }}) hour) as hora_local
from {{ source('bruto', 'eventos') }}
