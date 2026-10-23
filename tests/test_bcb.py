from datetime import date

from src.ingestao import armazenamento, bcb
from tests.conftest import RespostaFalsa, SessaoFalsa

RESPOSTAS = {
    "1": [{"data": "02/01/2026", "valor": "5.4321"}, {"data": "05/01/2026", "valor": "5.4400"}],
    "21619": [{"data": "02/01/2026", "valor": "6.3000000"}],
    # A meta Selic vem com datas futuras, que devem ser descartadas
    "432": [{"data": "02/01/2026", "valor": "15.00"}, {"data": "20/01/2026", "valor": "15.00"}],
}


def _responder(url, params):
    codigo = url.split("bcdata.sgs.")[1].split("/")[0]
    return RespostaFalsa(200, RESPOSTAS[codigo])


def test_coletar_serie_converte_tipos_e_parametros():
    sessao = SessaoFalsa(_responder)
    df = bcb.coletar_serie(1, date(2026, 1, 1), date(2026, 1, 10), sessao=sessao)
    assert df["valor"].tolist() == [5.4321, 5.44]
    assert df["serie_nome"].unique().tolist() == ["dolar_venda"]
    url, params = sessao.chamadas[0]
    assert url.endswith("bcdata.sgs.1/dados")
    assert params["dataInicial"] == "01/01/2026" and params["dataFinal"] == "10/01/2026"


def test_coletar_serie_descarta_datas_futuras():
    df = bcb.coletar_serie(432, date(2026, 1, 1), date(2026, 1, 10), sessao=SessaoFalsa(_responder))
    assert len(df) == 1


def test_coletar_serie_404_vira_vazio():
    df = bcb.coletar_serie(1, date(2026, 1, 1), date(2026, 1, 2), sessao=SessaoFalsa(lambda *_: RespostaFalsa(404, texto="")))
    assert df.empty


def test_coletar_serie_tenta_de_novo_em_erro_temporario():
    respostas = iter([RespostaFalsa(503, texto="indisponivel"), RespostaFalsa(200, RESPOSTAS["1"])])
    df = bcb.coletar_serie(1, date(2026, 1, 1), date(2026, 1, 10), sessao=SessaoFalsa(lambda *_: next(respostas)))
    assert len(df) == 2


def test_coletar_incremental_e_idempotente(dir_bruto):
    sessao = SessaoFalsa(_responder)
    assert bcb.coletar(dir_bruto, hoje=date(2026, 1, 10), sessao=sessao) == 4
    assert bcb.coletar(dir_bruto, hoje=date(2026, 1, 10), sessao=sessao) == 0
    # Segunda rodada começa no último registro menos a sobreposição
    _, params = sessao.chamadas[3]
    assert params["dataInicial"] == "01/01/2026"  # 05/01 - 5 dias, limitado ao início do estudo
    assert len(armazenamento.ler_fonte("bcb_sgs", dir_bruto)) == 4


def test_coletar_serie_tenta_de_novo_quando_vem_html():
    respostas = iter([RespostaFalsa(200, texto="<html>manutencao</html>"), RespostaFalsa(200, RESPOSTAS["1"])])
    df = bcb.coletar_serie(1, date(2026, 1, 1), date(2026, 1, 10), sessao=SessaoFalsa(lambda *_: next(respostas)))
    assert len(df) == 2
