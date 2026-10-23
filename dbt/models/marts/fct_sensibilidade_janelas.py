"""Sensibilidade de janela (diária): CAR e p-valor do teste principal em [0,0], [0,+1],
[-1,+3] (principal) e [-5,+5], com a mesma estimação da análise principal."""

from src.estatistica import robustez


def model(dbt, session):
    dbt.config(materialized="table")
    p = robustez.ler_parametros(dbt.config.get("parametros_robustez"))
    cfg = p["freq"]["diaria"]
    return robustez.sensibilidade(
        dbt.ref("resultados_eventos").df(),
        dbt.ref("int_retornos_diarios_ref").df(),
        dbt.ref("int_janelas_diarias").df(),
        p["janelas_sensibilidade"], cfg["est"], cfg["min_est"], cfg["jan"],
    )
