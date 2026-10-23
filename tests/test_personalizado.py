"""Evento personalizado do dashboard (src/estatistica/personalizado.py), com dados sintéticos."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.estatistica import personalizado as pz

JAN, EST, MIN_EST = (-1, 3), (-120, -11), 60
DIAS = pd.bdate_range("2025-01-01", periods=400)
CHOQUE_DIA = pd.Timestamp("2026-04-06")  # segunda-feira


def _retornos(choque: float = 0.0) -> pd.DataFrame:
    rng = np.random.default_rng(21)
    ref = rng.normal(0, 0.01, len(DIAS))
    r = 1.1 * ref + rng.normal(0, 0.004, len(DIAS))
    r[DIAS.get_loc(CHOQUE_DIA)] += choque
    return pd.DataFrame({"ativo": "X", "tempo": DIAS, "idx": np.arange(2, len(DIAS) + 2),
                         "log_retorno": r, "r_referencia": ref, "modelo_retorno_normal": "mercado"})


def _janelas_vazias():
    return pd.DataFrame(columns=["ativo", "idx", "fase", "evento_id"])


def test_domingo_17h_conta_a_partir_de_segunda():
    df = _retornos()
    idx0 = pz.idx_dia_zero(df, pd.Timestamp("2026-04-05 17:00"), "diaria", 17, -3)
    assert df.loc[df["idx"] == idx0, "tempo"].iloc[0] == CHOQUE_DIA
    # às 12h de segunda o dia 0 é a própria segunda; às 18h, a terça
    assert pz.idx_dia_zero(df, pd.Timestamp("2026-04-06 12:00"), "diaria", 17, -3) == idx0
    assert pz.idx_dia_zero(df, pd.Timestamp("2026-04-06 18:00"), "diaria", 17, -3) == idx0 + 1


def test_barra_zero_horaria_em_utc():
    barras = pd.DataFrame({"tempo": pd.to_datetime(["2026-04-06 12:00", "2026-04-06 13:00", "2026-04-06 14:00"]),
                           "idx": [1, 2, 3]})
    # 10h de Brasília = 13h UTC
    assert pz.idx_dia_zero(barras, pd.Timestamp("2026-04-06 10:00"), "horaria", 17, -3) == 2


def test_choque_na_data_escolhida_e_detectado():
    res, passos = pz.estudar(_retornos(0.05), _janelas_vazias(), "X", "2026-04-05 17:00", "diaria", JAN, EST, MIN_EST)
    assert res["car"] == pytest.approx(0.05, abs=0.015) and res["p_valor"] < 0.01
    assert passos["rel"].tolist() == [-1, 0, 1, 2, 3]
    assert passos["car_acumulado"].iloc[-1] == pytest.approx(res["car"])


def test_data_sem_choque_nao_significativa():
    res, _ = pz.estudar(_retornos(0.05), _janelas_vazias(), "X", "2026-02-01 17:00", "diaria", JAN, EST, MIN_EST)
    assert res["p_valor"] > 0.05


def test_janela_de_evento_real_sai_da_estimacao():
    df = _retornos()
    idx_real = df.loc[df["tempo"] == pd.Timestamp("2026-02-02"), "idx"].iloc[0]
    reais = pd.DataFrame({"ativo": "X", "idx": np.arange(idx_real - 1, idx_real + 4), "fase": "evento", "evento_id": 9})
    sem, _ = pz.estudar(df, _janelas_vazias(), "X", "2026-04-05 17:00", "diaria", JAN, EST, MIN_EST)
    com, _ = pz.estudar(df, reais, "X", "2026-04-05 17:00", "diaria", JAN, EST, MIN_EST)
    assert com["n_estimacao"] == sem["n_estimacao"] - 5
    # escolher a data do próprio evento real não exclui a janela dele
    proprio, _ = pz.estudar(df, reais, "X", "2026-02-01 17:00", "diaria", JAN, EST, MIN_EST)
    assert proprio["n_obs"] == 5


def test_futuro_sem_dados():
    res, passos = pz.estudar(_retornos(), _janelas_vazias(), "X", "2030-01-01 12:00", "diaria", JAN, EST, MIN_EST)
    assert res is None and passos.empty
