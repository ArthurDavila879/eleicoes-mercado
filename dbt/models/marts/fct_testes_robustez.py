"""Testes adicionais na janela principal: Patell, BMP e Corrado, com ajuste de Holm.

Calculados em Python (src/estatistica) com as mesmas regras dos modelos SQL; o teste
assert_robustez_igual_principal confere que CAR e t batem com resultados_eventos.
"""

from src.estatistica import robustez


def model(dbt, session):
    dbt.config(materialized="table")
    p = robustez.ler_parametros(dbt.config.get("parametros_robustez"))
    dados = {
        "diaria": (dbt.ref("int_retornos_diarios_ref").df(), dbt.ref("int_janelas_diarias").df()),
        "horaria": (dbt.ref("int_retornos_horarios_ref").df(), dbt.ref("int_janelas_horarias").df()),
    }
    return robustez.testes_adicionais(
        dbt.ref("resultados_eventos").df(), dados, p["freq"], p["familia_principal"])
