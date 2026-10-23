-- Nenhuma observação de evento fora das janelas configuradas
select * from {{ ref('fct_retornos_anormais') }}
where (frequencia = 'diaria'
       and rel not between {{ var('janela_diaria_inicio') }} and {{ var('janela_diaria_fim') }})
   or (frequencia = 'horaria'
       and rel not between {{ var('janela_horaria_inicio') }} and {{ var('janela_horaria_fim') }})
