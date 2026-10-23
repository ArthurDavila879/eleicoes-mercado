"""Resultado final por evento × ativo × frequência: CAR, p-valor bicaudal e significância.

O p-valor usa a distribuição t de Student com os graus de liberdade da janela de
estimação. É calculado para janelas completas e para janelas parciais com pelo menos
metade das observações esperadas (ex.: moedas na madrugada de domingo); o status
continua indicando a janela parcial.
"""

import numpy as np
from scipy import stats


def _estrelas(p):
    if p is None or np.isnan(p):
        return None
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else "n.s."


def model(dbt, session):
    dbt.config(materialized="table")
    car = dbt.ref("fct_car_eventos").df()
    eventos = dbt.ref("stg_eventos").df()[["evento_id", "tipo", "descricao", "data_hora_local"]]
    ativos = dbt.ref("ativos").df()[["ativo", "nome", "classe"]]

    t = car["estatistica_t"].astype(float).to_numpy()
    gl = car["graus_liberdade"].astype(float).to_numpy()
    status_ok = car["status"].isin(["completo", "janela_parcial"]).to_numpy()
    obs_suficientes = (car["n_obs"] * 2 >= car["n_esperado"]).to_numpy()
    valido = status_ok & obs_suficientes & ~np.isnan(t) & (np.nan_to_num(gl) > 0)
    p_valor = np.full(len(car), np.nan)
    p_valor[valido] = 2 * stats.t.sf(np.abs(t[valido]), gl[valido])
    car["p_valor"] = p_valor
    car["significancia"] = [_estrelas(p) for p in p_valor]
    # CAR em log-retorno convertido para variação percentual aproximada
    car["car_pct"] = (np.exp(car["car"].astype(float)) - 1) * 100

    resultado = car.merge(eventos, on="evento_id", how="left").merge(ativos, on="ativo", how="left")
    colunas = [
        "evento_id", "tipo", "descricao", "data_hora_local", "frequencia", "janela",
        "ativo", "nome", "classe", "modelo_retorno_normal", "status", "n_obs", "n_esperado",
        "inicio_janela", "fim_janela", "car", "car_pct", "erro_padrao_car", "estatistica_t",
        "graus_liberdade", "p_valor", "significancia", "alfa", "beta", "sigma", "n_estimacao",
    ]
    return resultado[colunas].sort_values(["evento_id", "frequencia", "ativo"]).reset_index(drop=True)
