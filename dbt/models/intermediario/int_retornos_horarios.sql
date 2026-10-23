-- Log-retornos de 1h por ativo. O retorno da 1ª barra do pregão inclui o intervalo
-- desde a última barra anterior (noite/fim de semana).
{{ log_retornos('stg_precos_horarios', 'data_hora_utc') }}
