-- Barra 0 = primeira barra de 1h que começa no instante do evento ou depois dele.
{{ janelas_evento(
    'int_retornos_horarios_ref',
    "data_hora_utc",
    var('estimacao_horaria_inicio'), var('estimacao_horaria_fim'),
    var('janela_horaria_inicio'), var('janela_horaria_fim')
) }}
