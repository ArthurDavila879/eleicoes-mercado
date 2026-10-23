-- Parâmetros do retorno normal por frequência × evento × ativo
select * from ({{ parametros_modelo('int_janelas_diarias', 'diaria') }})
union all
select * from ({{ parametros_modelo('int_janelas_horarias', 'horaria') }})
