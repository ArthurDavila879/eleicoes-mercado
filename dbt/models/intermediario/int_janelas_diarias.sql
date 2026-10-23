-- Dia 0 = primeiro pregão na data do evento; se o evento ocorre a partir da hora de corte
-- (fechamento da B3) ou fora de pregão, o dia 0 é o pregão seguinte.
{{ janelas_evento(
    'int_retornos_diarios_ref',
    "case when hora_local >= " ~ var('hora_corte_pregao') ~ " then data_local + 1 else data_local end",
    var('estimacao_diaria_inicio'), var('estimacao_diaria_fim'),
    var('janela_diaria_inicio'), var('janela_diaria_fim')
) }}
