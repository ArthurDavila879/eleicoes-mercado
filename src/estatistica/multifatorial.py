"""Modelo multifatorial adicional (diário): ``R = α + β_m·R_Ibov + β_f·R_fator + ε``.

Complementa o modelo de mercado simples (que continua sendo o principal) para ações cujo
preço depende de uma commodity: PETR4/PETR3 com o Brent e VALE3 com o minério de ferro
(``dbt/seeds/modelos_multifatoriais.csv``). Mesmas regras do estudo principal: dia 0, janelas,
exclusão das janelas de outros eventos, mínimo de observações e p-valor pela t de Student
(aqui com n − 3 graus de liberdade, σ² = SQR/(n − 3)).

O retorno do fator é medido entre os MESMOS dois pregões da ação (último preço do fator até
cada data, como o EEM no modelo do Ibovespa), para que feriados de só um dos mercados não
desalinhem as séries; não se usa preço do fator além do último coletado.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

COLUNAS = [
    "evento_id", "ativo", "fator", "status", "n_obs", "n_esperado", "n_estimacao", "alfa",
    "beta_mercado", "beta_fator", "p_beta_fator", "r2_simples", "r2_multifatorial", "car",
    "car_pct", "erro_padrao_car", "estatistica_t", "graus_liberdade", "p_valor",
]


def retorno_fator_alinhado(datas: pd.Series, precos_fator: pd.DataFrame) -> np.ndarray:
    """Log-retorno do fator entre cada data do ativo e a data anterior do ativo (ASOF).

    ``datas``: datas do ativo, em ordem; ``precos_fator``: colunas ``tempo`` e ``preco``.
    NaN na 1ª data e depois do último preço do fator.
    """
    f = precos_fator.dropna(subset=["preco"]).sort_values("tempo")
    if f.empty:
        return np.full(len(datas), np.nan)
    t_f = f["tempo"].to_numpy(dtype="datetime64[ns]")
    p_f = f["preco"].to_numpy(float)
    d = pd.to_datetime(datas).to_numpy(dtype="datetime64[ns]")
    pos = np.searchsorted(t_f, d, side="right") - 1  # último preço do fator até a data
    preco = np.where(pos >= 0, p_f[np.clip(pos, 0, None)], np.nan)
    r = np.full(len(d), np.nan)
    r[1:] = np.log(preco[1:] / preco[:-1])
    r[d > t_f.max()] = np.nan
    return r


def _ols(y: np.ndarray, x: np.ndarray):
    """MQO com intercepto. Retorna (coeficientes, resíduos, matriz (X'X)^-1)."""
    X = np.column_stack([np.ones(len(y)), x])
    xtx_inv = np.linalg.pinv(X.T @ X)
    coef = xtx_inv @ X.T @ y
    return coef, y - X @ coef, xtx_inv


def _r2(y: np.ndarray, residuo: np.ndarray) -> float:
    sst = ((y - y.mean()) ** 2).sum()
    return float(1 - (residuo**2).sum() / sst) if sst > 0 else np.nan


def estudo(
    idx: np.ndarray, y: np.ndarray, r_mercado: np.ndarray, r_fator: np.ndarray,
    idx0: int, jan: tuple[int, int], est: tuple[int, int], excluir: np.ndarray, min_est: int,
) -> dict | None:
    """Estudo de evento com o modelo de dois fatores para um dia 0 (``idx0``)."""
    rel = idx - idx0
    completo = ~np.isnan(y) & ~np.isnan(r_mercado) & ~np.isnan(r_fator)
    na_est = completo & (rel >= est[0]) & (rel <= est[1]) & ~np.isin(idx, excluir)
    na_jan = completo & (rel >= jan[0]) & (rel <= jan[1])
    n_est, n_obs, n_esperado = int(na_est.sum()), int(na_jan.sum()), jan[1] - jan[0] + 1
    if n_est < 5 or n_obs == 0:
        return None
    x_est = np.column_stack([r_mercado[na_est], r_fator[na_est]])
    coef, residuo, xtx_inv = _ols(y[na_est], x_est)
    gl = n_est - 3
    sigma2 = (residuo**2).sum() / gl
    _, residuo_simples, _ = _ols(y[na_est], r_mercado[na_est])
    ar = y[na_jan] - (coef[0] + coef[1] * r_mercado[na_jan] + coef[2] * r_fator[na_jan])
    car = ar.sum()
    ep = np.sqrt(n_obs * sigma2)
    t = car / ep if ep > 0 else np.nan
    status = ("estimacao_insuficiente" if n_est < min_est
              else "janela_parcial" if n_obs < n_esperado else "completo")
    valido = status != "estimacao_insuficiente" and 2 * n_obs >= n_esperado and np.isfinite(t)
    t_beta_f = coef[2] / np.sqrt(sigma2 * xtx_inv[2, 2]) if sigma2 > 0 else np.nan
    return dict(
        status=status, n_obs=n_obs, n_esperado=n_esperado, n_estimacao=n_est, alfa=coef[0],
        beta_mercado=coef[1], beta_fator=coef[2],
        p_beta_fator=float(2 * stats.t.sf(abs(t_beta_f), gl)) if np.isfinite(t_beta_f) else np.nan,
        r2_simples=_r2(y[na_est], residuo_simples), r2_multifatorial=_r2(y[na_est], residuo),
        car=car, car_pct=(np.exp(car) - 1) * 100, erro_padrao_car=ep, estatistica_t=t,
        graus_liberdade=gl, p_valor=float(2 * stats.t.sf(abs(t), gl)) if valido else np.nan,
    )


def estudar(
    retornos_ref: pd.DataFrame,
    janelas: pd.DataFrame,
    precos: pd.DataFrame,
    modelos: pd.DataFrame,
    jan: tuple[int, int],
    est: tuple[int, int],
    min_est: int,
) -> pd.DataFrame:
    """Para cada ativo × fator de ``modelos`` e cada evento com dia 0 na série do ativo.

    ``retornos_ref``: int_retornos_diarios_ref (usa ``r_mercado``, o Ibovespa no mesmo pregão);
    ``janelas``: int_janelas_diarias (dia 0 e janelas dos outros eventos);
    ``precos``: stg_precos_diarios (preços dos fatores).
    """
    linhas = []
    for m in modelos.itertuples():
        serie = retornos_ref[retornos_ref["ativo"] == m.ativo].sort_values("idx")
        if serie.empty:
            continue
        precos_fator = precos.loc[precos["ativo"] == m.fator, ["data", "preco"]].rename(columns={"data": "tempo"})
        precos_fator["tempo"] = pd.to_datetime(precos_fator["tempo"])
        # datas de TODOS os preços do ativo (o retorno do 1º pregão da série é nulo)
        r_f = retorno_fator_alinhado(serie["tempo"], precos_fator)
        idx = serie["idx"].to_numpy(np.int64)
        j = janelas[janelas["ativo"] == m.ativo]
        zeros = (j["idx"] - j["rel"]).groupby(j["evento_id"]).first()
        em_janela = j[j["fase"] == "evento"]
        for evento_id, idx0 in zeros.items():
            excluir = em_janela.loc[em_janela["evento_id"] != evento_id, "idx"].to_numpy()
            r = estudo(idx, serie["log_retorno"].to_numpy(float), serie["r_mercado"].to_numpy(float),
                       r_f, int(idx0), jan, est, excluir, min_est)
            linha = dict(evento_id=evento_id, ativo=m.ativo, fator=m.fator)
            if r is not None:
                linha.update(r)
            linhas.append(linha)
    return pd.DataFrame(linhas).reindex(columns=COLUNAS)
