"""p-valor empírico bicaudal do CAR real contra a distribuição placebo do mesmo ativo."""

from src.estatistica import robustez


def model(dbt, session):
    dbt.config(materialized="table")
    p = robustez.ler_parametros(dbt.config.get("parametros_robustez"))
    return robustez.resultados_placebo(
        dbt.ref("resultados_eventos").df(), dbt.ref("fct_placebo_distribuicao").df(),
        p["placebo_inicio"],
    )
