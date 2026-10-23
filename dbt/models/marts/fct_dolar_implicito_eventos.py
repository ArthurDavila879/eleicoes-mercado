"""Dólar implícito no bitcoin em torno dos eventos: sexta 17h → domingo (evento) → segunda
10h, com placebo nos outros fins de semana. Ver src/estatistica/dolar_implicito.py."""

from src.estatistica import dolar_implicito


def model(dbt, session):
    dbt.config(materialized="table")
    oficial = dbt.ref("stg_precos_horarios").df()
    eventos, _ = dolar_implicito.estudar(
        dbt.ref("stg_dolar_implicito_horario").df(),
        oficial[oficial["ativo"] == "BRL=X"],
        dbt.ref("stg_eventos").df(),
    )
    return eventos
