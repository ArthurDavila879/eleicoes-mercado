"""Modelo multifatorial adicional (diário): Ibovespa + Brent (PETR4, PETR3) e Ibovespa +
minério de ferro (VALE3), lado a lado com o modelo de mercado simples de resultados_eventos.
Ver src/estatistica/multifatorial.py."""

from src.estatistica import multifatorial, robustez


def model(dbt, session):
    dbt.config(materialized="table")
    cfg = robustez.ler_parametros(dbt.config.get("parametros_robustez"))["freq"]["diaria"]
    multi = multifatorial.estudar(
        dbt.ref("int_retornos_diarios_ref").df(),
        dbt.ref("int_janelas_diarias").df(),
        dbt.ref("stg_precos_diarios").df(),
        dbt.ref("modelos_multifatoriais").df(),
        cfg["jan"], cfg["est"], cfg["min_est"],
    )
    simples = dbt.ref("resultados_eventos").df()
    simples = simples.loc[simples["frequencia"] == "diaria",
                          ["evento_id", "ativo", "car", "car_pct", "p_valor", "beta"]].rename(
        columns={"car": "car_simples", "car_pct": "car_pct_simples", "p_valor": "p_valor_simples",
                 "beta": "beta_simples"})
    return multi.merge(simples, on=["evento_id", "ativo"], how="left")
