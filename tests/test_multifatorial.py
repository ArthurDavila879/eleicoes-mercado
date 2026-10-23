"""Modelo multifatorial (src/estatistica/multifatorial.py) com dados sintéticos."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.estatistica import multifatorial as mf

JAN, EST, MIN_EST = (-1, 3), (-120, -11), 60
N, DIA0 = 400, 300
B_M, B_F = 1.0, 0.5


def _dados(choque: float = 0.0, semente: int = 11):
    rng = np.random.default_rng(semente)
    r_m = rng.normal(0, 0.01, N)
    r_f = rng.normal(0, 0.02, N)
    y = 0.0002 + B_M * r_m + B_F * r_f + rng.normal(0, 0.005, N)
    y[DIA0] += choque
    return np.arange(1, N + 1), y, r_m, r_f


def _estudo(choque=0.0, semente=11):
    idx, y, r_m, r_f = _dados(choque, semente)
    return mf.estudo(idx, y, r_m, r_f, DIA0 + 1, JAN, EST, np.array([], int), MIN_EST)


def test_recupera_os_betas_e_ganha_r2():
    r = _estudo()
    assert r["beta_mercado"] == pytest.approx(B_M, abs=0.1)
    assert r["beta_fator"] == pytest.approx(B_F, abs=0.1) and r["p_beta_fator"] < 0.001
    assert r["r2_multifatorial"] > r["r2_simples"] + 0.2
    assert r["graus_liberdade"] == r["n_estimacao"] - 3 == 107


def test_sem_choque_nao_significativo():
    assert _estudo()["p_valor"] > 0.05


def test_choque_detectado():
    r = _estudo(choque=0.05)
    assert r["car"] == pytest.approx(0.05, abs=0.015) and r["p_valor"] < 0.01


def test_fator_irrelevante_da_quase_o_mesmo_car_do_modelo_simples():
    rng = np.random.default_rng(9)
    idx, y, r_m, _ = _dados(choque=0.03)
    ruido = rng.normal(0, 0.02, N)  # "fator" sem relação com a ação
    r = mf.estudo(idx, y - B_F * _dados()[3], r_m, ruido, DIA0 + 1, JAN, EST, np.array([], int), MIN_EST)
    assert abs(r["beta_fator"]) < 0.1 and r["p_valor"] < 0.01


def test_exclusao_e_status():
    idx, y, r_m, r_f = _dados()
    excluir = np.arange(DIA0 - 50, DIA0 - 40)
    r = mf.estudo(idx, y, r_m, r_f, DIA0 + 1, JAN, EST, excluir, MIN_EST)
    assert r["n_estimacao"] == 100 and r["status"] == "completo"
    r = mf.estudo(idx, y, r_m, r_f, 60, JAN, EST, np.array([], int), MIN_EST)  # 49 obs. antes
    assert r["status"] == "estimacao_insuficiente" and np.isnan(r["p_valor"])


def test_retorno_do_fator_entre_os_mesmos_pregoes():
    # Ação negocia seg–sex; o fator não tem a quarta (feriado só lá) nem a sexta (fim dos dados)
    datas = pd.Series(pd.to_datetime(["2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04", "2026-06-05"]))
    fator = pd.DataFrame({"tempo": pd.to_datetime(["2026-06-01", "2026-06-02", "2026-06-04"]),
                          "preco": [100.0, 110.0, 121.0]})
    r = mf.retorno_fator_alinhado(datas, fator)
    assert np.isnan(r[0])
    assert r[1] == pytest.approx(np.log(1.1))
    assert r[2] == pytest.approx(0.0)  # feriado do fator: retorno 0 nesse pregão
    assert r[3] == pytest.approx(np.log(1.1))  # a quinta acumula quarta + quinta do fator
    assert np.isnan(r[4])  # além do último preço do fator


def test_estudar_pelas_tabelas_do_dbt():
    idx, y, r_m, r_f = _dados(choque=0.05)
    datas = pd.bdate_range("2025-01-01", periods=N)
    precos_f = np.r_[100.0, 100.0 * np.exp(np.cumsum(r_f[1:]))]
    retornos = pd.DataFrame({"ativo": "PETR4.SA", "tempo": datas, "idx": idx, "log_retorno": y, "r_mercado": r_m})
    rel = idx - (DIA0 + 1)
    fase = np.where((rel >= JAN[0]) & (rel <= JAN[1]), "evento",
                    np.where((rel >= EST[0]) & (rel <= EST[1]), "estimacao", None))
    janelas = retornos.assign(evento_id=1, rel=rel, fase=fase)[fase != None]  # noqa: E711
    precos = pd.DataFrame({"ativo": "BZ=F", "data": datas, "preco": precos_f})
    modelos = pd.DataFrame({"ativo": ["PETR4.SA"], "fator": ["BZ=F"]})
    df = mf.estudar(retornos, janelas, precos, modelos, JAN, EST, MIN_EST)
    assert len(df) == 1 and df.loc[0, "p_valor"] < 0.01
    assert df.loc[0, "beta_fator"] == pytest.approx(B_F, abs=0.1)
