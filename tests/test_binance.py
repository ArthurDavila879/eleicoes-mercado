from datetime import date, datetime

import pandas as pd
import pytest

from src import config
from src.ingestao import armazenamento, binance
from tests.conftest import RespostaFalsa, SessaoFalsa

pytestmark = pytest.mark.usefixtures("sem_espera")

H = 3_600_000


def _kline(ms, preco):
    return [ms, str(preco), str(preco), str(preco), str(preco), "1.5", ms + H - 1, "0", 1, "0", "0", "0"]


def _responder_paginas(url, params):
    """Devolve até 1000 barras a partir de startTime, sem passar de endTime."""
    inicio, fim = params["startTime"], params["endTime"]
    barras = []
    ms = inicio
    while ms <= fim and len(barras) < params["limit"]:
        barras.append(_kline(ms, 100 + (ms - inicio) / H))
        ms += H
    return RespostaFalsa(200, barras)


def test_coletar_par_pagina_e_converte():
    sessao = SessaoFalsa(_responder_paginas)
    df = binance.coletar_par("BTCBRL", datetime(2026, 1, 1), datetime(2026, 3, 1), sessao)
    assert len(df) == 59 * 24  # jan + fev, de hora em hora
    assert len(sessao.chamadas) == 2  # 1416 barras = 2 páginas
    assert df["data_hora_utc"].iloc[0] == pd.Timestamp("2026-01-01 00:00")
    assert df["data_hora_utc"].is_unique and list(df.columns) == binance.COLUNAS


def test_coletar_incremental_e_idempotente(dir_bruto, monkeypatch):
    monkeypatch.setattr(config, "DATA_INICIO_CRIPTO", date(2026, 10, 1))
    sessao = SessaoFalsa(_responder_paginas)
    n1 = binance.coletar(dir_bruto, hoje=date(2026, 10, 3), sessao=sessao)
    assert n1 == 2 * 3 * 24  # dois pares, 3 dias
    sessao.chamadas.clear()
    assert binance.coletar(dir_bruto, hoje=date(2026, 10, 3), sessao=sessao) == 0
    # recomeça perto do último registro (sobreposição), não no início
    inicio = pd.to_datetime(sessao.chamadas[0][1]["startTime"], unit="ms")
    assert inicio >= pd.Timestamp("2026-10-01")
    assert len(armazenamento.ler_fonte("binance_horario", dir_bruto)) == n1


def test_falha_de_um_par_nao_derruba_o_outro(dir_bruto, monkeypatch):
    monkeypatch.setattr(config, "DATA_INICIO_CRIPTO", date(2026, 10, 1))

    def responder(url, params):
        if params["symbol"] == "BTCBRL":
            return RespostaFalsa(500, texto="erro")
        return _responder_paginas(url, params)

    assert binance.coletar(dir_bruto, hoje=date(2026, 10, 1), sessao=SessaoFalsa(responder)) == 24


def test_falha_total_levanta_erro(dir_bruto, monkeypatch):
    monkeypatch.setattr(config, "DATA_INICIO_CRIPTO", date(2026, 10, 1))
    with pytest.raises(RuntimeError):
        binance.coletar(dir_bruto, hoje=date(2026, 10, 1),
                        sessao=SessaoFalsa(lambda *_: RespostaFalsa(500, texto="erro")))
