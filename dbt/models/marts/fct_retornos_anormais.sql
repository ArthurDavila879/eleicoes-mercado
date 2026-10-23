-- Retornos anormais (AR) e CAR acumulado nas janelas [-1,+3] pregões e [-2h,+6h]
with ar as (
    {{ retornos_anormais('int_janelas_diarias', 'diaria') }}
    union all
    {{ retornos_anormais('int_janelas_horarias', 'horaria') }}
)

select
    *,
    sum(retorno_anormal) over (
        partition by frequencia, evento_id, ativo order by rel
        rows between unbounded preceding and current row
    ) as car_acumulado
from ar
