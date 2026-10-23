"""Análise agregada entre eventos (src/estatistica/agregado.py), com CARs sintéticos."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.estatistica import agregado

EP = 0.02  # erro-padrão do CAR de cada evento


def _resultados(cars: list[float], ativo: str = "X") -> pd.DataFrame:
    """Uma linha diária por evento, alternando 1º e 2º turno, um ano cada."""
    linhas = []
    for i, car in enumerate(cars):
        linhas.append(dict(
            frequencia="diaria", evento_id=i + 1, ativo=ativo, car=car, erro_padrao_car=EP,
            estatistica_t=car / EP, p_valor=0.5,
            descricao=f"{1 + i % 2}º turno: evento sintético",
            data_hora_local=pd.Timestamp(f"{2010 + i}-10-05 17:00"),
        ))
    return pd.DataFrame(linhas)


def _linha(df, grupo="todos"):
    return df[df["grupo"] == grupo].iloc[0]


def test_sem_choque_nada_significativo():
    rng = np.random.default_rng(1)
    r = _linha(agregado.caar(_resultados(list(rng.normal(0, EP, 8)))))
    assert r["n_eventos"] == 8
    assert r["p_agregado"] > 0.05 and r["p_transversal"] > 0.05 and r["p_qui2"] > 0.05


def test_choque_no_mesmo_sentido_detectado_pelo_caar():
    rng = np.random.default_rng(2)
    r = _linha(agregado.caar(_resultados(list(0.05 + rng.normal(0, EP, 8)))))
    assert r["caar"] == pytest.approx(0.05, abs=0.02)
    assert r["p_agregado"] < 0.01 and r["p_transversal"] < 0.01 and r["n_positivos"] == 8


def test_choques_em_sentidos_opostos_so_o_qui2_detecta():
    # Reações fortes que mudam de sinal entre eleições: a média se cancela, a magnitude não
    cars = [0.08, -0.08] * 4
    r = _linha(agregado.caar(_resultados(cars)))
    assert r["caar"] == pytest.approx(0.0, abs=1e-12)
    assert r["p_agregado"] > 0.5 and r["p_qui2"] < 1e-6


def test_grupos_por_turno():
    df = agregado.caar(_resultados([0.01, 0.02, 0.03, 0.04]))
    assert set(df["grupo"]) == {"todos", "1º turno", "2º turno"}
    assert _linha(df, "1º turno")["n_eventos"] == 2
    assert _linha(df, "2º turno")["eventos"] == "2011 2º turno, 2013 2º turno"
    assert np.isnan(_linha(df, "1º turno")["t_transversal"])  # precisa de N ≥ 3


def test_formulas():
    car, ep = np.array([0.03, 0.01, -0.01]), np.array([0.01, 0.02, 0.02])
    r = agregado.estatisticas(car, ep, car / ep)
    assert r["t_agregado"] == pytest.approx(0.03 / np.sqrt(0.0009))
    assert r["qui2_sem_direcao"] == pytest.approx(9 + 0.25 + 0.25)


def test_ignora_horario_e_eventos_sem_p_valor():
    df = _resultados([0.01, 0.02, 0.03])
    df.loc[0, "frequencia"] = "horaria"
    df.loc[1, "p_valor"] = np.nan
    assert _linha(agregado.caar(df))["n_eventos"] == 1
