select
    serie_codigo,
    serie_nome,
    cast(data as date) as data,
    valor
from {{ source('bruto', 'bcb_sgs') }}
