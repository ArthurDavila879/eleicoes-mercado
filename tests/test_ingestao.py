import pytest

from src import ingestao
from src.ingestao import bcb, gdelt, yahoo


@pytest.fixture
def coletores_falsos(monkeypatch):
    chamados = []
    for modulo, nome in [(bcb, "bcb_sgs"), (yahoo, "yahoo"), (gdelt, "gdelt")]:
        monkeypatch.setattr(modulo, "coletar", lambda nome=nome, **_: chamados.append(nome) or 1)
    return chamados


def test_coletar_tudo_roda_so_as_fontes_pedidas(coletores_falsos):
    assert ingestao.coletar_tudo(fontes=["bcb_sgs", "yahoo"]) == {"bcb_sgs": 1, "yahoo": 1}
    assert coletores_falsos == ["bcb_sgs", "yahoo"]


def test_coletar_tudo_recusa_fonte_desconhecida(coletores_falsos):
    with pytest.raises(ValueError, match="noticias"):
        ingestao.coletar_tudo(fontes=["noticias"])
