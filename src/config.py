"""Configuração central do projeto: caminhos, períodos e listas de séries/ativos."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIR_DADOS = RAIZ / "data"
DIR_BRUTO = DIR_DADOS / "bruto"
CAMINHO_EVENTOS = DIR_DADOS / "eventos.csv"
CAMINHO_DUCKDB = Path(os.environ.get("DUCKDB_PATH", DIR_DADOS / "eleicoes.duckdb"))
DIR_DBT = RAIZ / "dbt"

# Início do período de estudo (coleta desde esta data)
DATA_INICIO = date(2026, 1, 1)

FUSO_REFERENCIA = "America/Sao_Paulo"

# --- Banco Central: SGS (códigos confirmados no catálogo de dados abertos do BCB) ---
SERIES_SGS: dict[int, str] = {
    1: "dolar_venda",  # Taxa de câmbio - Livre - Dólar americano (venda) - diário
    21619: "euro_venda",  # Taxa de câmbio - Livre - Euro (venda) - diário
    432: "meta_selic",  # Taxa de juros - Meta Selic definida pelo Copom (% a.a.)
}

# --- Yahoo Finance ---
# Ativos brasileiros (Ibovespa, ações e real) e moedas de controle (emergentes).
# Todas as moedas estão cotadas como "unidades da moeda local por 1 USD".
ATIVOS_BRASIL = ["^BVSP", "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBAS3.SA", "BRL=X"]
MOEDAS_CONTROLE = ["MXN=X", "CLP=X", "COP=X", "ZAR=X"]
TICKERS_YAHOO = ATIVOS_BRASIL + MOEDAS_CONTROLE

# Sobreposição (re-coleta) para corrigir barras parciais/revisadas na coleta incremental
SOBREPOSICAO_DIAS_DIARIO = 5
SOBREPOSICAO_DIAS_HORARIO = 3

# --- GDELT (DOC 2.0) ---
# A MESMA consulta-base é aplicada a cada candidato do 2º turno (neutralidade).
# Candidatos em ordem alfabética do nome de urna usado na consulta.
CANDIDATOS_2_TURNO = ["Flávio Bolsonaro", "Lula"]
CONSULTA_BASE_GDELT = "{termo} sourcecountry:brazil"  # ver gdelt.montar_consulta
# A API DOC só pesquisa os últimos ~3 meses; a coleta incremental acumula o histórico.
JANELA_MAX_GDELT_DIAS = 89
SOBREPOSICAO_DIAS_GDELT = 7  # o GDELT revisa os dias mais recentes
