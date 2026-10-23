"""Dólar implícito no bitcoin (src/estatistica/dolar_implicito.py) com séries sintéticas."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.estatistica import dolar_implicito as di

EVENTO = pd.Timestamp("2026-06-14 20:00")  # domingo, 17h de Brasília
HORAS = pd.date_range("2025-06-01", "2026-07-31 23:00", freq="h")


def _horario(choque: float = 0.0, semente: int = 3) -> pd.DataFrame:
    """Dólar implícito com passeio aleatório; ``choque`` em log logo após o evento."""
    rng = np.random.default_rng(semente)
    r = rng.normal(0, 0.0008, len(HORAS))
    r[HORAS.get_loc(EVENTO + pd.Timedelta(hours=2))] += choque
    dolar = 5.0 * np.exp(np.cumsum(r))
    return pd.DataFrame({"data_hora_utc": HORAS, "dolar_implicito": dolar, "volume_btc": 2.0})


def _oficial(horario: pd.DataFrame) -> pd.DataFrame:
    # câmbio oficial só nos dias úteis, igual ao implícito nessas horas
    uteis = horario[horario["data_hora_utc"].dt.day_of_week < 5]
    return uteis.rename(columns={"dolar_implicito": "preco"})[["data_hora_utc", "preco"]]


def _eventos():
    return pd.DataFrame({"evento_id": [1], "data_hora_utc": [EVENTO]})


def test_instantes_do_fim_de_semana():
    sexta, ev, abertura = di.instantes(EVENTO)
    assert sexta == pd.Timestamp("2026-06-12 20:00") and abertura == pd.Timestamp("2026-06-15 13:00")


def test_valor_no_instante_e_o_fechamento_da_barra_que_termina_nele():
    s = pd.Series([1.0, 2.0], index=pd.to_datetime(["2026-06-14 19:00", "2026-06-14 20:00"]))
    assert di.valor_em(s, "2026-06-14 20:00") == 1.0
    assert np.isnan(di.valor_em(s, "2026-06-14 23:00"))
    assert di.valor_ate(s, "2026-06-14 23:00") == 2.0  # tolerância de 3 h


def test_sem_choque_nao_significativo():
    h = _horario()
    ev, dist = di.estudar(h, _oficial(h), _eventos())
    linha = ev.iloc[0]
    assert linha["n_placebo"] > 50 and linha["p_empirico"] > 0.05
    assert (dist["instante"].dt.day_of_week == 6).all()  # sempre domingos
    assert EVENTO not in set(dist["instante"])  # o próprio evento fica fora do placebo


def test_choque_detectado_e_medido():
    h = _horario(choque=-0.04)
    linha = di.estudar(h, _oficial(h), _eventos())[0].iloc[0]
    assert linha["reacao"] == pytest.approx(-0.04, abs=0.01)
    assert linha["p_empirico"] == pytest.approx(1 / (linha["n_placebo"] + 1))
    assert linha["fim_de_semana"] == pytest.approx(linha["pre_evento"] + linha["reacao"])
    # o oficial fecha na sexta e reabre na segunda: mede o fim de semana inteiro
    assert linha["oficial_fim_de_semana"] == pytest.approx(linha["fim_de_semana"], abs=1e-12)
    assert linha["agio_medio"] == pytest.approx(0.0, abs=1e-12)


def test_evento_sem_dados_de_bitcoin_fica_de_fora():
    h = _horario()
    eventos = pd.DataFrame({"evento_id": [1, 2], "data_hora_utc": [EVENTO, pd.Timestamp("2014-10-05 22:00")]})
    ev, _ = di.estudar(h, _oficial(h), eventos)
    assert ev["evento_id"].tolist() == [1]
