"""Volatilidade realizada e volume anormais (src/estatistica/atividade.py), com dados sintéticos."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.estatistica import atividade

JAN, EST, MIN_EST, CORTE = (-1, 3), (-120, -11), 60, 17
EVENTO_DIA = pd.Timestamp("2026-06-15")  # segunda-feira
EVENTOS = pd.DataFrame({"evento_id": [1], "data_local": [pd.Timestamp("2026-06-14")], "hora_local": [17]})


def _barras(fator_vol_evento: float = 1.0, semente: int = 3) -> pd.DataFrame:
    """Barras de 1h (13h–19h UTC) com volatilidade multiplicada no dia 0 e no dia +1."""
    rng = np.random.default_rng(semente)
    dias = pd.bdate_range("2025-11-03", "2026-07-31")
    linhas = []
    for d in dias:
        escala = fator_vol_evento if d in (EVENTO_DIA, EVENTO_DIA + pd.Timedelta(days=1)) else 1.0
        for h in range(13, 20):
            linhas.append((d + pd.Timedelta(hours=h), rng.normal(0, 0.003) * escala))
    return pd.DataFrame(linhas, columns=["tempo", "log_retorno"]).assign(ativo="X")


def _volumes(fator_volume_evento: float = 1.0, semente: int = 4) -> pd.DataFrame:
    rng = np.random.default_rng(semente)
    dias = pd.bdate_range("2025-11-03", "2026-07-31")
    v = np.exp(rng.normal(15, 0.25, len(dias)))
    v[dias.get_loc(EVENTO_DIA)] *= fator_volume_evento
    return pd.DataFrame({"ativo": "X", "data": dias, "volume": v})


def _estudar(series, medida):
    return atividade.estudar(series, medida, EVENTOS, JAN, EST, MIN_EST, CORTE).iloc[0]


def test_volatilidade_sem_choque_nao_significativa():
    r = _estudar(atividade.serie_volatilidade(_barras(), -3), "volatilidade_realizada")
    assert r["status"] == "completo" and r["n_obs"] == 5 and r["p_valor"] > 0.05


def test_volatilidade_com_choque_detectada():
    r = _estudar(atividade.serie_volatilidade(_barras(fator_vol_evento=4.0), -3), "volatilidade_realizada")
    # variância 16x nos dias 0 e +1: ln(16) ≈ 2,77 cada → acumulado ≈ 5,5
    assert r["anormal_acumulado"] == pytest.approx(2 * np.log(16), abs=1.5)
    assert r["p_valor"] < 0.01 and r["anormal_dia0_pct"] > 500


def test_volume_sem_choque_nao_significativo():
    assert _estudar(atividade.serie_volume(_volumes()), "volume")["p_valor"] > 0.05


def test_volume_com_choque_detectado():
    r = _estudar(atividade.serie_volume(_volumes(fator_volume_evento=8.0)), "volume")
    assert r["anormal_dia0_pct"] == pytest.approx(700, abs=250)
    assert r["p_valor"] < 0.01


def test_dia_zero_de_evento_de_domingo_e_a_segunda():
    r = _estudar(atividade.serie_volume(_volumes()), "volume")
    assert pd.Timestamp(r["inicio_janela"]) == pd.Timestamp("2026-06-12")  # dia -1 = sexta
    assert atividade.inicio_evento(pd.Timestamp("2026-06-15"), 12, CORTE) == EVENTO_DIA


def test_dia_incompleto_descartado_na_volatilidade():
    barras = _barras()
    ultimo = barras["tempo"].max().normalize()
    barras = barras[(barras["tempo"].dt.normalize() < ultimo) | (barras["tempo"].dt.hour == 13)]
    serie = atividade.serie_volatilidade(barras, -3)
    assert serie["data"].max() < ultimo  # só 1 barra no último dia (pregão em andamento)
