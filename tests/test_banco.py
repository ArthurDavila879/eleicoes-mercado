"""Reconstrução automática do DuckDB pelo dashboard (src/banco.py), sem rodar o dbt."""

from __future__ import annotations

import pandas as pd
import pytest

from src import banco, config
from src.ingestao import armazenamento


@pytest.fixture
def raiz(tmp_path, monkeypatch):
    """Repositório mínimo: um Parquet, eventos e um modelo dbt."""
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "eventos.csv").write_text("data_hora,tipo\n", encoding="utf-8")
    df = pd.DataFrame({"ticker": ["X"], "data": [pd.Timestamp("2026-01-02")], "fechamento": [1.0]})
    armazenamento.salvar_incremental(df, "yahoo_diario", ["ticker", "data"], "data", tmp_path / "data" / "bruto")
    (tmp_path / "dbt" / "models").mkdir(parents=True)
    (tmp_path / "dbt" / "models" / "m.sql").write_text("select 1", encoding="utf-8")
    monkeypatch.setattr(config, "RAIZ", tmp_path)
    return tmp_path


def test_impressao_muda_com_dados_e_com_modelos(raiz):
    inicial = banco.impressao_digital()
    assert banco.impressao_digital() == inicial  # estável
    df = pd.DataFrame({"ticker": ["X"], "data": [pd.Timestamp("2026-01-05")], "fechamento": [2.0]})
    armazenamento.salvar_incremental(df, "yahoo_diario", ["ticker", "data"], "data", raiz / "data" / "bruto")
    com_dado_novo = banco.impressao_digital()
    assert com_dado_novo != inicial
    (raiz / "dbt" / "models" / "m.sql").write_text("select 2", encoding="utf-8")
    assert banco.impressao_digital() != com_dado_novo


def test_constroi_quando_falta_e_nao_repete(raiz):
    db = raiz / "data" / "teste.duckdb"
    chamadas = []

    def construir(caminho):
        chamadas.append(caminho)
        caminho.write_bytes(b"banco")
        return True

    assert banco.garantir_banco(db, construir) == "construido"
    assert banco.garantir_banco(db, construir) == "atual"
    assert chamadas == [db]


def test_reconstroi_quando_os_dados_mudam(raiz):
    db = raiz / "data" / "teste.duckdb"
    db.write_bytes(b"banco")
    banco.gravar_impressao(db)
    assert banco.banco_atualizado(db)
    (raiz / "data" / "eventos.csv").write_text("data_hora,tipo\nnovo\n", encoding="utf-8")
    assert not banco.banco_atualizado(db)
    assert banco.garantir_banco(db, lambda c: True) == "construido"
    assert banco.banco_atualizado(db)


def test_falha_na_construcao_nao_grava_impressao(raiz):
    db = raiz / "data" / "teste.duckdb"
    assert banco.garantir_banco(db, lambda c: False) == "falhou"
    assert not banco.caminho_impressao(db).exists()
