"""Testes dos cálculos de robustez (src/estatistica) com dados sintéticos, sem dbt.

Para cada teste estatístico: um caso sem choque (não deve ser significativo) e um com
choque conhecido injetado na janela do evento (deve ser detectado).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.estatistica import estudo_evento as ee
from src.estatistica import robustez

JAN = (-1, 3)
EST = (-120, -11)
N_DIAS = 600
DIA0 = 400
BETA = 1.2


def _serie(choque_por_dia: dict[int, float] | None = None, semente: int = 7, modelo="mercado",
           escala_evento: float = 1.0) -> ee.Serie:
    """Série diária sintética com modelo de mercado; choques somados em dias relativos ao
    DIA0. ``escala_evento`` multiplica o ruído na janela (aumento de variância sem média)."""
    rng = np.random.default_rng(semente)
    tempo = pd.bdate_range("2024-01-01", periods=N_DIAS)
    ref = rng.normal(0, 0.01, N_DIAS)
    ruido = rng.normal(0, 0.005, N_DIAS)
    ruido[DIA0 + JAN[0]:DIA0 + JAN[1] + 1] *= escala_evento
    r = 0.0002 + BETA * ref + ruido
    for rel, choque in (choque_por_dia or {}).items():
        r[DIA0 + rel] += choque
    if modelo == "controle_moedas":
        r = ref + ruido
    return ee.Serie(idx=np.arange(1, N_DIAS + 1), tempo=tempo.to_numpy(), r=r,
                    ref=np.zeros(N_DIAS) if modelo == "media_constante" else ref, modelo=modelo)


def _idx0():
    return DIA0 + 1  # idx começa em 1


# --- estudo principal reproduzido -------------------------------------------------------

def test_estimacao_recupera_beta_e_janela():
    r = ee.estudo(_serie(), _idx0(), JAN, EST, min_estimacao=60)
    assert r["beta"] == pytest.approx(BETA, abs=0.1)
    assert r["n_obs"] == 5 and r["n_estimacao"] == 110 and r["status"] == "completo"


def test_exclusao_de_outra_janela_reduz_a_estimacao():
    excluir = np.arange(_idx0() - 50, _idx0() - 45)
    r = ee.estudo(_serie(), _idx0(), JAN, EST, excluir, min_estimacao=60)
    assert r["n_estimacao"] == 105


@pytest.mark.parametrize("modelo", ["mercado", "media_constante", "controle_moedas"])
def test_sem_choque_nada_significativo(modelo):
    r = ee.estudo(_serie(modelo=modelo), _idx0(), JAN, EST, min_estimacao=60)
    for p in ["p_valor", "p_patell", "p_bmp", "p_corrado"]:
        assert r[p] > 0.05, p


def test_choque_de_um_dia_detectado_por_t_e_patell():
    r = ee.estudo(_serie({0: 0.05}), _idx0(), JAN, EST, min_estimacao=60)
    assert r["car"] == pytest.approx(0.05, abs=0.015)
    assert r["p_valor"] < 0.01 and r["p_patell"] < 0.01


def test_choque_persistente_detectado_por_bmp_e_corrado():
    # +2% em todos os dias da janela: todos os AR no topo dos postos e SAR homogêneos
    r = ee.estudo(_serie({k: 0.02 for k in range(-1, 4)}), _idx0(), JAN, EST, min_estimacao=60)
    assert r["p_bmp"] < 0.01
    assert r["p_corrado"] < 0.01
    assert r["p_valor"] < 0.01 and r["p_patell"] < 0.01


def test_bmp_robusto_a_aumento_de_variancia_sem_media():
    # Variância 6x maior na janela, sem retorno anormal médio: o t principal tende a
    # rejeitar com frequência; o BMP (dispersão da própria janela) não deveria
    rejeicoes_t = rejeicoes_bmp = 0
    for semente in range(60):
        r = ee.estudo(_serie(semente=semente, escala_evento=6.0), _idx0(), JAN, EST, min_estimacao=60)
        rejeicoes_t += r["p_valor"] < 0.05
        rejeicoes_bmp += r["p_bmp"] < 0.05
    assert rejeicoes_t > 20
    assert rejeicoes_bmp <= 8  # ~5% esperado


def test_patell_corrige_erro_de_previsao():
    p = ee.estimar(np.array([0.01, 0.02, 0.0, -0.01]), np.array([0.01, 0.02, -0.01, 0.0]), "mercado")
    c = ee.fator_previsao("mercado", np.array([p["media_ref"], p["media_ref"] + 0.05]), p)
    assert c[0] == pytest.approx(1 + 1 / 4)
    assert c[1] > c[0]
    assert ee.fator_previsao("controle_moedas", np.zeros(2), p).tolist() == [1.0, 1.0]


def test_bmp_nao_calculado_com_menos_de_3_obs():
    r = ee.estudo(_serie({0: 0.05}), _idx0(), (0, 1), EST, min_estimacao=60)
    assert np.isnan(r["p_bmp"]) and r["p_valor"] < 0.01


def test_estimacao_insuficiente_sem_p_valor():
    r = ee.estudo(_serie(), 80, JAN, EST, min_estimacao=100)
    assert r["status"] == "estimacao_insuficiente" and np.isnan(r["p_valor"])


# --- placebo ----------------------------------------------------------------------------

def _placebo(serie, restrito=False, n=1000):
    reais = np.arange(_idx0() + JAN[0], _idx0() + JAN[1] + 1)
    return ee.placebo(serie, "diaria", JAN, EST, reais, 60, n,
                      ee.semente_grupo(20261025, "X", "diaria", "v"), restrito)


def test_placebo_sem_choque_nao_significativo():
    serie = _serie()
    real = ee.estudo(serie, _idx0(), JAN, EST, min_estimacao=60)
    dist = _placebo(serie)
    assert ee.p_empirico(real["car"], dist["car"].to_numpy()) > 0.05


def test_placebo_com_choque_significativo():
    serie = _serie({0: 0.05})
    real = ee.estudo(serie, _idx0(), JAN, EST, min_estimacao=60)
    dist = _placebo(serie)
    p = ee.p_empirico(real["car"], dist["car"].to_numpy())
    assert p == pytest.approx(1 / (1 + len(dist)))


def test_placebo_nao_toca_a_janela_real_e_e_reprodutivel():
    serie = _serie()
    dist = _placebo(serie)
    assert len(dist) > 300 and dist["idx0"].is_unique
    proibidos = set(range(_idx0() + JAN[0] - JAN[1], _idx0() + JAN[1] - JAN[0] + 1))
    assert not proibidos & set(dist["idx0"])
    # janela inteira dentro dos dados e estimação mínima
    assert dist["idx0"].max() + JAN[1] <= N_DIAS and dist["idx0"].min() >= 60
    pd.testing.assert_frame_equal(dist, _placebo(serie))


def test_placebo_limita_a_n_e_restrito_usa_inicio_de_semana():
    serie = _serie()
    assert len(_placebo(serie, n=50)) == 50
    dist = _placebo(serie, restrito=True)
    assert (pd.to_datetime(dist["tempo0"]).dt.day_of_week == 0).all()  # segundas (sem feriados)


def test_inicio_de_sessao_horario():
    tempo = pd.to_datetime(["2026-06-12 18:00", "2026-06-12 19:00", "2026-06-15 13:00",
                            "2026-06-15 14:00", "2026-06-16 13:00"]).to_numpy()
    assert ee.inicio_de_sessao(tempo, "horaria").tolist() == [False, False, True, False, True]


def test_p_empirico_formula():
    assert ee.p_empirico(0.05, np.array([0.01, -0.06, 0.02])) == pytest.approx(2 / 4)
    assert np.isnan(ee.p_empirico(np.nan, np.array([0.1])))


def test_holm():
    p = np.array([0.01, 0.04, np.nan, 0.03])
    ajustado = ee.holm(p)
    assert ajustado[0] == pytest.approx(0.03)  # 3 × 0,01
    assert ajustado[3] == pytest.approx(0.06)  # 2 × 0,03
    assert ajustado[1] == pytest.approx(0.06)  # max(1 × 0,04; anterior)
    assert np.isnan(ajustado[2])


# --- orquestração (formato das tabelas do dbt) -------------------------------------------

def _tabelas(serie: ee.Serie, ativo="PETR4.SA"):
    retornos = pd.DataFrame({"ativo": ativo, "tempo": serie.tempo, "idx": serie.idx,
                             "log_retorno": serie.r, "r_referencia": serie.ref,
                             "modelo_retorno_normal": serie.modelo})
    rel = serie.idx - _idx0()
    fase = np.where((rel >= JAN[0]) & (rel <= JAN[1]), "evento",
                    np.where((rel >= EST[0]) & (rel <= EST[1]), "estimacao", None))
    janelas = retornos.assign(evento_id=1, rel=rel, fase=fase)[fase != None]  # noqa: E711
    real = ee.estudo(serie, _idx0(), JAN, EST, min_estimacao=60)
    resultados = pd.DataFrame([{"frequencia": "diaria", "evento_id": 1, "ativo": ativo,
                                "car": real["car"], "p_valor": real["p_valor"]}])
    return retornos, janelas, resultados


def test_sensibilidade_detecta_choque_nas_janelas_que_o_contem():
    retornos, janelas, resultados = _tabelas(_serie({0: 0.05}))
    df = robustez.sensibilidade(resultados, retornos, janelas,
                                [(0, 0), (0, 1), (-1, 3), (-5, 5), (2, 3)], EST, 60, JAN)
    p = df.set_index("janela")["p_valor"]
    assert p["[0,0]"] < 0.01 and p["[0,+1]"] < 0.01 and p["[-1,+3]"] < 0.01 and p["[-5,+5]"] < 0.01
    assert p["[+2,+3]"] > 0.05  # janela que não contém o dia do choque
    assert df.loc[df["principal"], "janela"].tolist() == ["[-1,+3]"]


def test_sensibilidade_sem_choque_nao_significativa():
    retornos, janelas, resultados = _tabelas(_serie())
    df = robustez.sensibilidade(resultados, retornos, janelas, [(0, 0), (0, 1), (-1, 3), (-5, 5)],
                                EST, 60, JAN)
    assert (df["p_valor"] > 0.05).all()


def test_testes_adicionais_e_placebo_pela_orquestracao():
    retornos, janelas, resultados = _tabelas(_serie({0: 0.05}))
    cfg = {"diaria": dict(jan=JAN, est=EST, min_est=60)}
    testes = robustez.testes_adicionais(resultados, {"diaria": (retornos, janelas)}, cfg, ["PETR4.SA"])
    assert testes.loc[0, "car"] == pytest.approx(resultados.loc[0, "car"])
    assert testes.loc[0, "p_patell"] < 0.01 and testes.loc[0, "p_valor_holm"] < 0.01
    dist = robustez.placebo(resultados, {"diaria": (retornos, janelas)}, cfg, 200, 1)
    assert set(dist["versao"]) == {"restrita", "irrestrita"}
    res = robustez.resultados_placebo(resultados, dist)
    assert (res["p_empirico"] < 0.05).all()


def test_ler_parametros_do_dbt():
    p = robustez.ler_parametros(
        '{"janela_diaria_inicio": -1, "janela_diaria_fim": 3, "janela_horaria_inicio": -2,'
        ' "janela_horaria_fim": 5, "estimacao_diaria_inicio": -120, "estimacao_diaria_fim": -11,'
        ' "estimacao_horaria_inicio": -300, "estimacao_horaria_fim": -11,'
        ' "min_obs_estimacao_diaria": 60, "min_obs_estimacao_horaria": 150,'
        ' "familia_principal": ["^BVSP"], "janelas_sensibilidade": "0,0;-5,5",'
        ' "placebo_n": 1000, "placebo_semente": 20261025}')
    assert p["freq"]["horaria"]["jan"] == (-2, 5)
    assert p["janelas_sensibilidade"] == [(0, 0), (-5, 5)]
    assert p["placebo_semente"] == 20261025


def test_placebo_com_inicio_ignora_dados_anteriores():
    # Cortar a série em ``inicio`` equivale a rodar o placebo numa série que começa ali
    serie = _serie()
    inicio = pd.Timestamp(serie.tempo[150])
    reais = np.arange(_idx0() + JAN[0], _idx0() + JAN[1] + 1)
    rng = lambda: ee.semente_grupo(1, "X", "diaria", "v")  # noqa: E731
    cortada = _placebo_com(serie, reais, rng(), inicio=str(inicio.date()))
    manter = np.arange(N_DIAS) > 150  # o 1º retorno a partir do corte também sai
    sub = ee.Serie(serie.idx[manter], serie.tempo[manter], serie.r[manter], serie.ref[manter], serie.modelo)
    pd.testing.assert_frame_equal(cortada, _placebo_com(sub, reais, rng()))
    assert pd.to_datetime(cortada["tempo0"]).min() > inicio


def _placebo_com(serie, reais, rng, inicio=None):
    return ee.placebo(serie, "diaria", JAN, EST, reais, 60, 1000, rng, False, inicio)
