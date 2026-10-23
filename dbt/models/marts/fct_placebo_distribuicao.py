"""Placebo: CAR de pseudoeventos em datas sem evento (mesma metodologia do estudo real).

Por ativo × frequência × versão (restrita: pseudodia 0 em início de sessão; irrestrita:
qualquer pregão/barra), até placebo_n datas sorteadas sem reposição com semente fixa.
"""

from src.estatistica import robustez


def model(dbt, session):
    dbt.config(materialized="table")
    p = robustez.ler_parametros(dbt.config.get("parametros_robustez"))
    dados = {
        "diaria": (dbt.ref("int_retornos_diarios_ref").df(), dbt.ref("int_janelas_diarias").df()),
        "horaria": (dbt.ref("int_retornos_horarios_ref").df(), dbt.ref("int_janelas_horarias").df()),
    }
    return robustez.placebo(
        dbt.ref("resultados_eventos").df(), dados, p["freq"], p["placebo_n"], p["placebo_semente"],
        p["placebo_inicio"])
