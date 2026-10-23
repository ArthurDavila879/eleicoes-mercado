-- p-valor entre 0 e 1; obrigatório em janelas completas; ausente sem dados ou estimação
select * from {{ ref('resultados_eventos') }}
where (p_valor is not null and (p_valor < 0 or p_valor > 1))
   or (status = 'completo' and p_valor is null)
   or (status in ('aguardando_dados', 'estimacao_insuficiente') and p_valor is not null)
   or (status = 'janela_parcial' and p_valor is not null and n_obs * 2 < n_esperado)
