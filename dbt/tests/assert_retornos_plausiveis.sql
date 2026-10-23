-- Log-retornos finitos e sem saltos absurdos (|r| > 50% indica erro de dado)
select * from {{ ref('int_retornos_diarios') }}
where log_retorno is not null and (isinf(log_retorno) or isnan(log_retorno) or abs(log_retorno) > 0.5)
union all
select * from {{ ref('int_retornos_horarios') }}
where log_retorno is not null and (isinf(log_retorno) or isnan(log_retorno) or abs(log_retorno) > 0.5)
