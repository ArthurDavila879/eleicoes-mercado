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
# Histórico de preços (Yahoo diário e BCB/SGS) desde 2014, para estudar as eleições de 2014,
# 2018 e 2022 (só na frequência diária). O placebo continua usando só datas desde 2023, como
# no pré-registro (var placebo_inicio do dbt). As janelas de estimação dos eventos de 2026 não
# mudam com o histórico mais longo.
DATA_INICIO_PRECOS = date(2014, 1, 1)
# O Yahoo só fornece barras de 1h dos últimos ~730 dias; margem de segurança
HISTORICO_MAX_HORARIO_DIAS = 720
# Tolerância para considerar o histórico completo (o 1º dia pode ser feriado/fim de semana)
TOLERANCIA_HISTORICO_DIAS = 7

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
# PRIO3 só entra na carteira long-short PETR4 − PRIO3 (dbt/seeds/carteiras.csv).
# AXIA3 = Eletrobras (ELET3 até a troca de nome para AXIA Energia; o Yahoo não tem mais ELET3.SA).
ATIVOS_BRASIL = [
    "^BVSP", "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBAS3.SA", "PRIO3.SA", "BRL=X",
    "PETR3.SA", "BBDC4.SA", "AXIA3.SA", "SBSP3.SA", "CMIG4.SA", "MRVE3.SA", "COGN3.SA", "MGLU3.SA",
]
MOEDAS_CONTROLE = ["MXN=X", "CLP=X", "COP=X", "ZAR=X"]
# Mercado global para o modelo de mercado do Ibovespa: ETF iShares MSCI Emerging Markets
# (NYSE, em USD). Só diário: as barras de 1h dos EUA começam na meia hora (13:30 UTC) e
# não se alinham às da B3.
MERCADO_GLOBAL = "EEM"
# Fatores e indicadores globais (só diário): Brent e minério de ferro (modelos multifatoriais),
# índice do dólar (DXY), VIX e juro de 10 anos dos EUA (^TNX = taxa × 10), para contexto.
FATORES_GLOBAIS = ["BZ=F", "TIO=F", "DX-Y.NYB", "^VIX", "^TNX"]
# Bitcoin em dólar (diário e 1h): checagem cruzada do dólar implícito (ver binance.py)
CRIPTO_YAHOO = ["BTC-USD"]
TICKERS_YAHOO = ATIVOS_BRASIL + MOEDAS_CONTROLE + [MERCADO_GLOBAL] + FATORES_GLOBAIS + CRIPTO_YAHOO
TICKERS_SO_DIARIO = [MERCADO_GLOBAL] + FATORES_GLOBAIS

# --- Binance (dados públicos de mercado): bitcoin em reais e em USDT, barras de 1h ---
PARES_BINANCE = ["BTCBRL", "BTCUSDT"]
# O par BTCBRL existe desde 13/10/2020; a coleta começa em nov/2020 (inclui as eleições de 2022)
DATA_INICIO_CRIPTO = date(2020, 11, 1)

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
