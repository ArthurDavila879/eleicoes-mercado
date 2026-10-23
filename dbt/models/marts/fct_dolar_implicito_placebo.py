"""Distribuição placebo da reação do dólar implícito (mesmo intervalo em outros fins de semana)."""

from src.estatistica import dolar_implicito


def model(dbt, session):
    dbt.config(materialized="table")
    oficial = dbt.ref("stg_precos_horarios").df()
    _, distribuicao = dolar_implicito.estudar(
        dbt.ref("stg_dolar_implicito_horario").df(),
        oficial[oficial["ativo"] == "BRL=X"],
        dbt.ref("stg_eventos").df(),
    )
    return distribuicao
