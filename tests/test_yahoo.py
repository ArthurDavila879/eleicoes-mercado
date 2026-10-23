from datetime import date

import pandas as pd
import pytest

from src.ingestao import armazenamento, yahoo


def _diario(ticker, inicio, fim, intervalo):
    indice = pd.DatetimeIndex(pd.to_datetime(["2026-10-01", "2026-10-02"])).tz_localize("America/Sao_Paulo")
    return pd.DataFrame(
        {"Open": [10.0, 11.0], "High": [11.0, 12.0], "Low": [9.0, 10.0], "Close": [10.5, 11.5],
         "Adj Close": [10.4, 11.4], "Volume": [100, 200]}, index=indice)


def _horario(ticker, inicio, fim, intervalo):
    # Duas barras na hora cheia e uma linha "ao vivo" às 11:37 (deve ser descartada)
    indice = pd.DatetimeIndex(pd.to_datetime(
        ["2026-10-05 10:00", "2026-10-05 11:00", "2026-10-05 11:37"])).tz_localize("America/Sao_Paulo")
    return pd.DataFrame({"Open": [1.0, 2, 3], "High": [1.0, 2, 3], "Low": [1.0, 2, 3],
                         "Close": [1.0, 2, 3], "Volume": [1, 2, 3]}, index=indice)


def _baixar_falso(ticker, inicio, fim, intervalo):
    return _diario(ticker, inicio, fim, intervalo) if intervalo == "1d" else _horario(ticker, inicio, fim, intervalo)


def test_coletar_ticker_diario():
    df = yahoo.coletar_ticker("PETR4.SA", date(2026, 10, 1), date(2026, 10, 3), "1d", _diario)
    assert list(df.columns) == yahoo.COLUNAS_DIARIO
    assert df["data"].tolist() == [pd.Timestamp("2026-10-01"), pd.Timestamp("2026-10-02")]
    assert df["fechamento_ajustado"].tolist() == [10.4, 11.4]


def test_coletar_ticker_horario_em_utc_e_sem_linha_ao_vivo():
    df = yahoo.coletar_ticker("PETR4.SA", date(2026, 10, 5), date(2026, 10, 6), "1h", _horario)
    assert df["data_hora_utc"].tolist() == [pd.Timestamp("2026-10-05 13:00"), pd.Timestamp("2026-10-05 14:00")]


def test_coletar_ticker_vazio():
    vazio = lambda *_: pd.DataFrame()
    assert yahoo.coletar_ticker("X", date(2026, 1, 1), date(2026, 1, 2), "1d", vazio).empty


def test_coletar_todos_incremental_e_idempotente(dir_bruto):
    chamadas = []

    def baixar(ticker, inicio, fim, intervalo):
        chamadas.append((ticker, inicio, fim, intervalo))
        return _baixar_falso(ticker, inicio, fim, intervalo)

    r1 = yahoo.coletar(dir_bruto, hoje=date(2026, 10, 5), baixar=baixar, tickers=["PETR4.SA", "BRL=X"])
    assert r1 == {"yahoo_diario": 4, "yahoo_horario": 4}
    assert chamadas[0][1] == date(2023, 1, 1) and chamadas[0][2] == date(2026, 10, 6)
    chamadas.clear()
    r2 = yahoo.coletar(dir_bruto, hoje=date(2026, 10, 5), baixar=baixar, tickers=["PETR4.SA", "BRL=X"])
    assert r2 == {"yahoo_diario": 0, "yahoo_horario": 0}
    # Segunda coleta começa perto do último registro, não em 01/01
    assert chamadas[0][1] == date(2026, 9, 27)
    assert len(armazenamento.ler_fonte("yahoo_horario", dir_bruto)) == 4


def test_falha_em_um_ticker_nao_derruba_os_demais(dir_bruto):
    def baixar(ticker, inicio, fim, intervalo):
        if ticker == "RUIM":
            raise ConnectionError("sem rede")
        return _baixar_falso(ticker, inicio, fim, intervalo)

    r = yahoo.coletar(dir_bruto, hoje=date(2026, 10, 5), baixar=baixar, tickers=["RUIM", "BRL=X"])
    assert r["yahoo_diario"] == 2


def test_falha_total_levanta_erro(dir_bruto):
    def baixar(*_):
        raise ConnectionError("sem rede")

    with pytest.raises(RuntimeError):
        yahoo.coletar(dir_bruto, hoje=date(2026, 10, 5), baixar=baixar, tickers=["A"])


def test_busca_historico_anterior_ao_primeiro_registro(dir_bruto):
    # Séries já coletadas a partir de out/2026: a próxima coleta busca o que falta antes
    yahoo.coletar(dir_bruto, hoje=date(2026, 10, 5), baixar=_baixar_falso, tickers=["PETR4.SA"])
    chamadas = []

    def baixar(ticker, inicio, fim, intervalo):
        chamadas.append((intervalo, inicio, fim))
        return _baixar_falso(ticker, inicio, fim, intervalo)

    yahoo.coletar(dir_bruto, hoje=date(2026, 10, 5), baixar=baixar, tickers=["PETR4.SA"])
    assert ("1d", date(2023, 1, 1), date(2026, 10, 1)) in chamadas
    # Barras de 1h: só até o limite do Yahoo (720 dias antes de hoje)
    assert ("1h", date(2024, 10, 15), date(2026, 10, 5)) in chamadas


def test_historico_completo_nao_e_rebuscado(dir_bruto):
    antigo = pd.DataFrame({"ticker": "PETR4.SA", "data": pd.to_datetime(["2023-01-02", "2026-10-02"]),
                           "abertura": 1.0, "maxima": 1.0, "minima": 1.0, "fechamento": 1.0,
                           "fechamento_ajustado": 1.0, "volume": 1.0})
    armazenamento.salvar_incremental(antigo, "yahoo_diario", ["ticker", "data"], "data", dir_bruto)
    chamadas = []

    def baixar(ticker, inicio, fim, intervalo):
        chamadas.append((intervalo, inicio, fim))
        return _baixar_falso(ticker, inicio, fim, intervalo)

    yahoo.coletar(dir_bruto, hoje=date(2026, 10, 5), baixar=baixar, tickers=["PETR4.SA"])
    assert [c for c in chamadas if c[0] == "1d"] == [("1d", date(2026, 9, 27), date(2026, 10, 6))]
