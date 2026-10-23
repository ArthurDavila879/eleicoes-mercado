-- A janela de estimação termina antes da janela do evento (sem sobreposição)
select * from {{ ref('int_janelas_diarias') }}
where fase = 'estimacao' and rel >= {{ var('janela_diaria_inicio') }}
union all
select * from {{ ref('int_janelas_horarias') }}
where fase = 'estimacao' and rel >= {{ var('janela_horaria_inicio') }}
