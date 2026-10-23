import pandas as pd
import pytest

from src import config
from src.eventos import validacao

CABECALHO = "data_hora,tipo,descricao,fonte_url\n"


def _escrever(tmp_path, linhas):
    caminho = tmp_path / "eventos.csv"
    caminho.write_text(CABECALHO + linhas, encoding="utf-8")
    return caminho


def test_arquivo_valido_converte_para_utc(tmp_path):
    caminho = _escrever(tmp_path, "2026-10-04T17:00:00-03:00,resultado,Fim da votação,https://www.tse.jus.br/x\n")
    df = validacao.carregar(caminho)
    assert df["data_hora_utc"].iloc[0] == pd.Timestamp("2026-10-04 20:00")
    assert df["evento_id"].tolist() == [1]


@pytest.mark.parametrize("linha, trecho", [
    ("2026-10-04 17:00,resultado,x,https://a.b/c", "ISO 8601"),          # sem fuso
    ("2026-02-30T10:00:00-03:00,resultado,x,https://a.b/c", "inexistente"),
    ("2026-10-04T17:00:00-03:00,comicio,x,https://a.b/c", "tipo"),
    ("2026-10-04T17:00:00-03:00,resultado,,https://a.b/c", "descricao"),
    ("2026-10-04T17:00:00-03:00,resultado,x,tse.jus.br", "fonte_url"),
])
def test_linhas_invalidas_sao_rejeitadas(tmp_path, linha, trecho):
    with pytest.raises(validacao.EventosInvalidos, match=trecho):
        validacao.carregar(_escrever(tmp_path, linha + "\n"))


def test_colunas_erradas(tmp_path):
    caminho = tmp_path / "e.csv"
    caminho.write_text("data,tipo\n2026-10-04,resultado\n", encoding="utf-8")
    with pytest.raises(validacao.EventosInvalidos, match="colunas"):
        validacao.carregar(caminho)


def test_duplicados(tmp_path):
    linha = "2026-10-04T17:00:00-03:00,resultado,x,https://a.b/c\n"
    with pytest.raises(validacao.EventosInvalidos, match="duplicado"):
        validacao.carregar(_escrever(tmp_path, linha * 2))


def test_arquivo_do_projeto_e_valido():
    if not config.CAMINHO_EVENTOS.exists():
        pytest.skip("data/eventos.csv ainda não existe")
    df = validacao.carregar()
    assert len(df) > 0
