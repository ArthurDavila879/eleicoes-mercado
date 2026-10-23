from datetime import date

import pytest

from src import config
from src.ingestao import armazenamento, gdelt
from tests.conftest import RespostaFalsa, SessaoFalsa

VOLUME = {"query_details": {}, "timeline": [{"series": "Article Count", "data": [
    {"date": "20261003T000000Z", "value": 120, "norm": 50000},
    {"date": "20261004T000000Z", "value": 900, "norm": 52000}]}]}
TOM = {"query_details": {}, "timeline": [{"series": "Average Tone", "data": [
    {"date": "20261003T000000Z", "value": -1.5},
    {"date": "20261004T000000Z", "value": -2.25}]}]}


def _responder(url, params):
    return RespostaFalsa(200, VOLUME if params["mode"] == "timelinevolraw" else TOM)


def test_mesma_consulta_base_para_todos_os_candidatos():
    consultas = [gdelt.montar_consulta(c) for c in config.CANDIDATOS_2_TURNO]
    moldes = {c.replace(f'"{nome}"', "{X}").replace(nome, "{X}")
              for c, nome in zip(consultas, config.CANDIDATOS_2_TURNO)}
    assert moldes == {"{X} sourcecountry:brazil"}  # só o nome muda
    assert gdelt.montar_consulta("Flávio Bolsonaro") == '"Flávio Bolsonaro" sourcecountry:brazil'
    assert gdelt.montar_consulta("Lula") == "Lula sourcecountry:brazil"


def test_coletar_candidato_junta_volume_e_tom():
    sessao = SessaoFalsa(_responder)
    df = gdelt.coletar_candidato("Lula", date(2026, 10, 3), date(2026, 10, 4), sessao=sessao, espera=0)
    assert df["n_artigos"].tolist() == [120, 900]
    assert df["tom_medio"].tolist() == [-1.5, -2.25]
    assert df["consulta"].iloc[0] == "Lula sourcecountry:brazil"
    params = sessao.chamadas[0][1]
    assert params["startdatetime"] == "20261003000000" and params["timelineres"] == "day"


def test_limite_de_requisicoes_tenta_de_novo():
    respostas = iter([RespostaFalsa(200, texto="Please limit requests to one every 5 seconds"),
                      RespostaFalsa(200, VOLUME), RespostaFalsa(200, TOM)])
    df = gdelt.coletar_candidato("Lula", date(2026, 10, 3), date(2026, 10, 4),
                                 sessao=SessaoFalsa(lambda *_: next(respostas)), espera=0)
    assert len(df) == 2


def test_limite_persistente_levanta_erro():
    sessao = SessaoFalsa(lambda *_: RespostaFalsa(429, texto="Please limit requests"))
    with pytest.raises(gdelt.LimiteRequisicoes):
        gdelt.coletar_candidato("Lula", date(2026, 10, 3), date(2026, 10, 4), sessao=sessao, espera=0)


def test_resposta_vazia_vira_dataframe_vazio():
    sessao = SessaoFalsa(lambda *_: RespostaFalsa(200, {"timeline": []}))
    assert gdelt.coletar_candidato("Lula", date(2026, 10, 3), date(2026, 10, 4), sessao=sessao, espera=0).empty


def test_coletar_incremental_respeita_janela_de_3_meses(dir_bruto):
    sessao = SessaoFalsa(_responder)
    n = gdelt.coletar(dir_bruto, hoje=date(2026, 10, 4), sessao=sessao, espera=0)
    assert n == 2 * len(config.CANDIDATOS_2_TURNO)
    # Primeira coleta: no máximo 89 dias para trás (limite da API DOC)
    assert sessao.chamadas[0][1]["startdatetime"] == "20260707000000"
    assert gdelt.coletar(dir_bruto, hoje=date(2026, 10, 4), sessao=sessao, espera=0) == 0
    assert len(armazenamento.ler_fonte("gdelt_diario", dir_bruto)) == 4


def test_tom_indisponivel_salva_volume_e_preserva_tom_antigo(dir_bruto):
    sessao = SessaoFalsa(_responder)
    gdelt.coletar(dir_bruto, hoje=date(2026, 10, 4), sessao=sessao, espera=0)

    def sem_tom(url, params):
        if params["mode"] == "timelinetone":
            return RespostaFalsa(200, texto="Please limit requests to one every 5 seconds")
        return RespostaFalsa(200, VOLUME)

    gdelt.coletar(dir_bruto, hoje=date(2026, 10, 4), sessao=SessaoFalsa(sem_tom), espera=0)
    lido = armazenamento.ler_fonte("gdelt_diario", dir_bruto)
    assert lido["tom_medio"].notna().all()
