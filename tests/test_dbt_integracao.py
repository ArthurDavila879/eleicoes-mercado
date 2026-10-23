"""Teste de integração do dbt com dados sintéticos (sem rede).

Gera preços com retornos aleatórios pequenos, injeta um retorno anormal conhecido no
dia/barra 0 do evento para PETR4 e para o real, roda carga + ``dbt build`` num DuckDB
temporário e confere se o estudo de evento recupera o efeito com significância.
"""

from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd
import pytest

from src import pipeline
from src.ingestao import armazenamento, carga

EVENTO_LOCAL = "2026-06-15T12:00:00-03:00"  # segunda-feira, durante o pregão
CHOQUE_DIARIO = 0.08
CHOQUE_HORARIO = 0.03
BETA_PETR4 = 1.2


def _precos(retornos: np.ndarray, inicial: float = 100.0) -> np.ndarray:
    return inicial * np.exp(np.cumsum(retornos))


def _dados_sinteticos(dir_bruto):
    rng = np.random.default_rng(42)

    # --- diário: dias úteis de jan a jul/2026 ---
    dias = pd.bdate_range("2026-01-02", "2026-07-31")
    dia0 = dias.get_loc(pd.Timestamp("2026-06-15"))
    n = len(dias)
    r_ibov = rng.normal(0, 0.005, n)
    r_petr = 0.0001 + BETA_PETR4 * r_ibov + rng.normal(0, 0.004, n)
    r_petr[dia0] += CHOQUE_DIARIO
    controles = {t: rng.normal(0, 0.004, n) for t in ["MXN=X", "CLP=X", "COP=X", "ZAR=X"]}
    media_controles = np.mean(list(controles.values()), axis=0)
    r_brl = media_controles + rng.normal(0, 0.003, n)
    r_brl[dia0] += CHOQUE_DIARIO

    linhas = []
    for ticker, r in {"^BVSP": r_ibov, "PETR4.SA": r_petr, "BRL=X": r_brl, **controles}.items():
        p = _precos(r)
        linhas.append(pd.DataFrame({
            "ticker": ticker, "data": dias, "abertura": p, "maxima": p, "minima": p,
            "fechamento": p, "fechamento_ajustado": p, "volume": 1000.0}))
    armazenamento.salvar_incremental(pd.concat(linhas), "yahoo_diario", ["ticker", "data"], "data", dir_bruto)

    # --- horário: barras 13h–19h UTC (10h–16h em Brasília) de abr a jul/2026 ---
    barras = pd.DatetimeIndex([d + pd.Timedelta(hours=h)
                               for d in pd.bdate_range("2026-04-01", "2026-07-31") for h in range(13, 20)])
    barra0 = barras.get_loc(pd.Timestamp("2026-06-15 15:00"))
    m = len(barras)
    rh_ibov = rng.normal(0, 0.002, m)
    rh_petr = BETA_PETR4 * rh_ibov + rng.normal(0, 0.0015, m)
    rh_petr[barra0] += CHOQUE_HORARIO
    controles_h = {t: rng.normal(0, 0.0015, m) for t in ["MXN=X", "CLP=X", "COP=X", "ZAR=X"]}
    rh_brl = np.mean(list(controles_h.values()), axis=0) + rng.normal(0, 0.001, m)
    rh_brl[barra0] += CHOQUE_HORARIO
    linhas = []
    for ticker, r in {"^BVSP": rh_ibov, "PETR4.SA": rh_petr, "BRL=X": rh_brl, **controles_h}.items():
        p = _precos(r)
        linhas.append(pd.DataFrame({
            "ticker": ticker, "data_hora_utc": barras, "abertura": p, "maxima": p,
            "minima": p, "fechamento": p, "volume": 1000.0}))
    armazenamento.salvar_incremental(
        pd.concat(linhas), "yahoo_horario", ["ticker", "data_hora_utc"], "data_hora_utc", dir_bruto)


@pytest.fixture(scope="module")
def banco(tmp_path_factory):
    raiz = tmp_path_factory.mktemp("dbt")
    dir_bruto = raiz / "bruto"
    dir_bruto.mkdir()
    _dados_sinteticos(dir_bruto)
    eventos = raiz / "eventos.csv"
    eventos.write_text(
        "data_hora,tipo,descricao,fonte_url\n"
        f"{EVENTO_LOCAL},outro,Evento sintético de teste,https://exemplo.org/teste\n"
        # Evento futuro, ainda sem dados: deve aparecer como aguardando_dados
        "2026-12-01T12:00:00-03:00,outro,Evento futuro de teste,https://exemplo.org/futuro\n",
        encoding="utf-8")
    db = raiz / "teste.duckdb"
    carga.carregar(db, dir_bruto, eventos)

    mp = pytest.MonkeyPatch()
    mp.setenv("DUCKDB_PATH", str(db))
    try:
        ok = pipeline.rodar_dbt("build", ["--target-path", str(raiz / "target"), "--log-path", str(raiz / "logs")])
    finally:
        mp.undo()
    assert ok, "dbt build falhou com os dados sintéticos"
    # O dbt-duckdb mantém a conexão aberta no mesmo processo: abrir com a mesma configuração
    con = duckdb.connect(str(db))
    yield con
    con.close()


def _resultado(con, ativo, frequencia, evento_id=1):
    return con.execute(
        "select status, car, p_valor, significancia, beta, n_obs from marts.resultados_eventos "
        "where ativo = ? and frequencia = ? and evento_id = ?", [ativo, frequencia, evento_id]
    ).fetchall()[0]


@pytest.mark.parametrize("ativo, frequencia, choque", [
    ("PETR4.SA", "diaria", CHOQUE_DIARIO),
    ("BRL=X", "diaria", CHOQUE_DIARIO),
    ("PETR4.SA", "horaria", CHOQUE_HORARIO),
    ("BRL=X", "horaria", CHOQUE_HORARIO),
])
def test_choque_injetado_e_detectado(banco, ativo, frequencia, choque):
    status, car, p_valor, significancia, _, _ = _resultado(banco, ativo, frequencia)
    assert status == "completo"
    assert car == pytest.approx(choque, abs=0.02)
    assert p_valor < 0.01 and significancia == "***"


def test_beta_do_modelo_de_mercado(banco):
    _, _, _, _, beta, n_obs = _resultado(banco, "PETR4.SA", "diaria")
    assert beta == pytest.approx(BETA_PETR4, abs=0.2)
    assert n_obs == 5  # janela [-1, +3]


def test_ibovespa_sem_choque_nao_e_significativo(banco):
    status, _, p_valor, _, _, _ = _resultado(banco, "^BVSP", "diaria")
    assert status == "completo" and p_valor > 0.01


def test_evento_futuro_fica_aguardando_dados(banco):
    status, car, p_valor, *_ = _resultado(banco, "PETR4.SA", "diaria", evento_id=2)
    assert status == "aguardando_dados" and car is None and p_valor is None


def test_barra_zero_e_a_primeira_apos_o_evento(banco):
    tempo = banco.execute(
        "select tempo from marts.fct_retornos_anormais "
        "where frequencia = 'horaria' and ativo = 'PETR4.SA' and evento_id = 1 and rel = 0"
    ).fetchall()[0][0]
    assert tempo == pd.Timestamp("2026-06-15 15:00")  # 12:00 em Brasília
