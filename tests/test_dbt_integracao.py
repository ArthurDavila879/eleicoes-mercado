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
CHOQUE_LONG_SHORT = 0.06
BETA_IBOV_EEM = 0.8
FERIADO_EUA = pd.Timestamp("2026-05-25")  # Memorial Day: B3 abre, NYSE fecha


def _precos(retornos: np.ndarray, inicial: float = 100.0) -> np.ndarray:
    return inicial * np.exp(np.cumsum(retornos))


def _dados_sinteticos(dir_bruto):
    rng = np.random.default_rng(42)

    # --- diário: dias úteis de jan a jul/2026 ---
    dias = pd.bdate_range("2026-01-02", "2026-07-31")
    dia0 = dias.get_loc(pd.Timestamp("2026-06-15"))
    n = len(dias)
    r_eem = rng.normal(0, 0.006, n)
    r_ibov = BETA_IBOV_EEM * r_eem + rng.normal(0, 0.003, n)
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
    # Mercado global (só diário), sem o pregão do feriado americano
    p = _precos(r_eem)
    eem = pd.DataFrame({"ticker": "EEM", "data": dias, "abertura": p, "maxima": p, "minima": p,
                        "fechamento": p, "fechamento_ajustado": p, "volume": 1000.0})
    linhas.append(eem[eem["data"] != FERIADO_EUA])
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

    # --- carteira long-short (Fase 2): BBAS3 com choque, ITUB4 sem; gerador próprio para não
    # mudar os sorteios acima ---
    rng_ls = np.random.default_rng(99)
    r_bbas = 1.0 * r_ibov + rng_ls.normal(0, 0.004, n)
    r_bbas[dia0] += CHOQUE_LONG_SHORT
    r_itub = 0.9 * r_ibov + rng_ls.normal(0, 0.004, n)
    linhas = []
    for ticker, r in {"BBAS3.SA": r_bbas, "ITUB4.SA": r_itub}.items():
        p = _precos(r)
        volume = np.exp(rng_ls.normal(15, 0.2, n))
        linhas.append(pd.DataFrame({
            "ticker": ticker, "data": dias, "abertura": p, "maxima": p, "minima": p,
            "fechamento": p, "fechamento_ajustado": p, "volume": volume}))
    armazenamento.salvar_incremental(pd.concat(linhas), "yahoo_diario", ["ticker", "data"], "data", dir_bruto)


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


def test_ibovespa_usa_mercado_global_so_no_diario(banco):
    modelos = dict(banco.execute(
        "select frequencia, modelo_retorno_normal from marts.resultados_eventos "
        "where ativo = '^BVSP' and evento_id = 1").fetchall())
    assert modelos == {"diaria": "mercado_global", "horaria": "media_constante"}
    _, _, _, _, beta, _ = _resultado(banco, "^BVSP", "diaria")
    assert beta == pytest.approx(BETA_IBOV_EEM, abs=0.15)


def test_retorno_global_alinhado_aos_pregoes_do_ibovespa(banco):
    # No feriado americano o ETF não negocia: retorno de referência 0 nesse pregão da B3,
    # e o pregão seguinte acumula os dois dias do ETF (sem lacuna nem dupla contagem)
    linhas = dict(banco.execute(
        "select cast(tempo as date), r_referencia from intermediario.int_retornos_diarios_ref "
        "where ativo = '^BVSP' and tempo between '2026-05-22' and '2026-05-26'").fetchall())
    assert linhas[FERIADO_EUA.date()] == pytest.approx(0.0)
    assert linhas[pd.Timestamp("2026-05-26").date()] != pytest.approx(0.0)
    assert banco.execute("select count(*) from marts.resultados_eventos where ativo = 'EEM'").fetchone()[0] == 0


def test_evento_futuro_fica_aguardando_dados(banco):
    status, car, p_valor, *_ = _resultado(banco, "PETR4.SA", "diaria", evento_id=2)
    assert status == "aguardando_dados" and car is None and p_valor is None


def test_barra_zero_e_a_primeira_apos_o_evento(banco):
    tempo = banco.execute(
        "select tempo from marts.fct_retornos_anormais "
        "where frequencia = 'horaria' and ativo = 'PETR4.SA' and evento_id = 1 and rel = 0"
    ).fetchall()[0][0]
    assert tempo == pd.Timestamp("2026-06-15 15:00")  # 12:00 em Brasília


# --- Robustez (Fase 1): mesmos dados sintéticos, marts novos ---------------------------

def _robustez(con, ativo, frequencia="diaria"):
    return con.execute(
        "select p_patell, p_bmp, p_corrado, p_valor_holm, car from marts.fct_testes_robustez "
        "where ativo = ? and frequencia = ? and evento_id = 1", [ativo, frequencia]).fetchone()


@pytest.mark.parametrize("ativo, frequencia", [
    ("PETR4.SA", "diaria"), ("BRL=X", "diaria"), ("PETR4.SA", "horaria"), ("BRL=X", "horaria")])
def test_robustez_patell_detecta_choque(banco, ativo, frequencia):
    p_patell, *_ = _robustez(banco, ativo, frequencia)
    assert p_patell < 0.01


def test_robustez_sem_choque_nao_significativa(banco):
    p_patell, p_bmp, p_corrado, *_ = _robustez(banco, "^BVSP")
    assert p_patell > 0.05 and p_bmp > 0.05 and p_corrado > 0.05


def test_holm_na_familia_principal(banco):
    linhas = banco.execute(
        "select ativo, p_valor, p_valor_holm, n_familia_holm from marts.fct_testes_robustez "
        "where frequencia = 'diaria' and evento_id = 1 and familia_principal "
        "and p_valor is not null").fetchall()
    # Nos dados sintéticos não há VALE3.SA: a família fica com 5 p-valores
    assert {l[0] for l in linhas} == {"^BVSP", "PETR4.SA", "BRL=X", "BBAS3.SA", "ITUB4.SA"}
    assert all(l[3] == 5 and l[2] >= l[1] for l in linhas)


def test_placebo_detecta_choque_e_nao_o_ibovespa(banco):
    res = dict(banco.execute(
        "select ativo, p_empirico from marts.fct_placebo_resultados "
        "where frequencia = 'diaria' and evento_id = 1 and versao = 'irrestrita'").fetchall())
    n = banco.execute(
        "select count(*) from marts.fct_placebo_distribuicao "
        "where frequencia = 'diaria' and ativo = 'PETR4.SA' and versao = 'irrestrita'").fetchone()[0]
    assert n > 20
    assert res["PETR4.SA"] == pytest.approx(1 / (n + 1))  # nenhum placebo tão extremo
    assert res["^BVSP"] > 0.05


def test_sensibilidade_de_janela(banco):
    p = dict(banco.execute(
        "select janela, p_valor from marts.fct_sensibilidade_janelas "
        "where ativo = 'PETR4.SA' and evento_id = 1").fetchall())
    assert set(p) == {"[0,0]", "[0,+1]", "[-1,+3]", "[-5,+5]"}
    assert all(v < 0.01 for v in p.values())  # todas contêm o dia 0 do choque



# --- Fase 2: carteira long-short e atividade anormal ---------------------------------

def test_long_short_detecta_choque_da_ponta_comprada(banco):
    status, car, p_valor, *_ = _resultado(banco, "LS_BBAS3_ITUB4", "diaria")
    assert status == "completo"
    assert car == pytest.approx(CHOQUE_LONG_SHORT, abs=0.02)
    assert p_valor < 0.01


def test_long_short_e_a_diferenca_dos_log_retornos(banco):
    dif = banco.execute(
        "select max(abs(c.log_retorno - (l.log_retorno - s.log_retorno))) "
        "from intermediario.int_retornos_diarios c "
        "join intermediario.int_retornos_diarios l on l.ativo = 'BBAS3.SA' and l.tempo = c.tempo "
        "join intermediario.int_retornos_diarios s on s.ativo = 'ITUB4.SA' and s.tempo = c.tempo "
        "where c.ativo = 'LS_BBAS3_ITUB4'").fetchone()[0]
    assert dif < 1e-12


def test_ponta_vendida_sem_choque_nao_significativa(banco):
    _, _, p_valor, *_ = _resultado(banco, "ITUB4.SA", "diaria")
    assert p_valor > 0.05


def test_atividade_anormal_calculada(banco):
    linhas = banco.execute(
        "select medida, ativo, status, p_valor from marts.fct_atividade_anormal where evento_id = 1"
    ).fetchall()
    medidas = {(m, a): (st, p) for m, a, st, p in linhas}
    assert medidas[("volume", "BBAS3.SA")][0] == "completo"
    assert medidas[("volume", "BBAS3.SA")][1] > 0.05  # volume sem choque
    # Barras de 1h só desde abril: menos de 60 dias de estimação antes de 15/06
    assert medidas[("volatilidade_realizada", "PETR4.SA")][0] == "estimacao_insuficiente"



# --- Fase 4: atualização das fontes (dias úteis) -----------------------------------------

@pytest.mark.parametrize("hoje, atualizado", [
    ("2026-08-03", True),   # segunda: último dado na sexta, 31/07
    ("2026-08-05", True),   # quarta: segunda e terça sem dado = 2 dias úteis (limite)
    ("2026-08-06", False),  # quinta: 3 dias úteis sem dado
])
def test_atualizacao_das_fontes_em_dias_uteis(banco, monkeypatch, tmp_path, hoje, atualizado):
    caminho = banco.execute("select path from duckdb_databases() where database_name = current_database()").fetchone()[0]
    monkeypatch.setenv("DUCKDB_PATH", caminho)
    ok = pipeline.rodar_dbt("test", [
        "--select", "tag:atualizacao", "--vars", f"{{data_referencia_atualizacao: '{hoje}'}}",
        "--target-path", str(tmp_path / "target"), "--log-path", str(tmp_path / "logs")])
    assert ok is atualizado



# --- Rodada 3: análise agregada entre eventos ---------------------------------------------

def test_caar_com_um_evento(banco):
    linha = banco.execute(
        "select n_eventos, caar, p_agregado, t_transversal from marts.fct_caar_eventos "
        "where grupo = 'todos' and ativo = 'PETR4.SA'").fetchone()
    car = _resultado(banco, "PETR4.SA", "diaria")[1]
    assert linha[0] == 1 and linha[1] == pytest.approx(car) and linha[2] < 0.01
    assert linha[3] is None or np.isnan(linha[3])  # transversal exige 3 eventos
