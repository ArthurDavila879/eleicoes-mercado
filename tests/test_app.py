"""Testes do dashboard com o AppTest do Streamlit (sem navegador)."""

from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

from src import config
from tests.test_dbt_integracao import banco  # noqa: F401  (fixture do banco sintético)


def _rodar(monkeypatch, caminho):
    monkeypatch.setattr(config, "CAMINHO_DUCKDB", caminho)
    app = AppTest.from_file(str(config.RAIZ / "app.py"), default_timeout=60)
    app.run()
    return app


def test_sem_banco_mostra_instrucoes(monkeypatch, tmp_path):
    app = _rodar(monkeypatch, tmp_path / "nao_existe.duckdb")
    assert not app.exception
    assert any("python -m src.pipeline" in e.value for e in app.error)
    assert any("Não é recomendação de investimento" in w.value for w in app.warning)


def test_dashboard_com_dados(monkeypatch, tmp_path, banco):  # noqa: F811
    # O dbt mantém a conexão aberta no processo (e o Windows trava o arquivo): o app lê
    # uma cópia feita pelo próprio DuckDB
    copia = tmp_path / "copia.duckdb"
    atual = banco.execute("select current_database()").fetchall()[0][0]
    banco.execute(f"attach '{copia.as_posix()}' as copia")
    banco.execute(f"copy from database {atual} to copia")
    banco.execute("detach copia")

    app = _rodar(monkeypatch, copia)
    assert not app.exception, app.exception
    assert len(app.tabs) == 5
    assert len(app.dataframe) >= 1  # tabela de CAR
    # Troca para a frequência horária e para o 2º evento (sem dados): sem erros
    app.sidebar.radio[0].set_value("horaria").run()
    assert not app.exception
    app.sidebar.selectbox[0].set_value(2).run()
    assert not app.exception
