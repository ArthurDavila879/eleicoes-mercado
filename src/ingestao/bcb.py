"""Coleta de séries do SGS (Sistema Gerenciador de Séries Temporais) do Banco Central.

Documentação: https://dadosabertos.bcb.gov.br/ — endpoint
``https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json&dataInicial=...``
"""

from __future__ import annotations

import logging
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

from src import config
from src.ingestao import armazenamento

log = logging.getLogger(__name__)

FONTE = "bcb_sgs"
URL_SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
COLUNAS = ["serie_codigo", "serie_nome", "data", "valor"]


def coletar_serie(
    codigo: int,
    inicio: date,
    fim: date,
    sessao: requests.Session | None = None,
    tentativas: int = 3,
) -> pd.DataFrame:
    """Baixa uma série do SGS entre ``inicio`` e ``fim`` (inclusive)."""
    sessao = sessao or requests.Session()
    params = {
        "formato": "json",
        "dataInicial": inicio.strftime("%d/%m/%Y"),
        "dataFinal": fim.strftime("%d/%m/%Y"),
    }
    url = URL_SGS.format(codigo=codigo)
    registros = None
    for tentativa in range(1, tentativas + 1):
        try:
            resp = sessao.get(url, params=params, timeout=60)
            # O SGS responde 404 quando não há valores no intervalo pedido
            if resp.status_code == 404:
                return pd.DataFrame(columns=COLUNAS)
            resp.raise_for_status()
            registros = resp.json()  # às vezes vem HTML de manutenção com HTTP 200
            break
        except (requests.RequestException, ValueError, RuntimeError) as erro:
            log.warning("SGS %s: %s (tentativa %s)", codigo, erro, tentativa)
            if tentativa == tentativas:
                raise
            time.sleep(5 * tentativa)

    if not registros:
        return pd.DataFrame(columns=COLUNAS)
    df = pd.DataFrame(registros)
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y").dt.date
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df["serie_codigo"] = codigo
    df["serie_nome"] = config.SERIES_SGS.get(codigo, str(codigo))
    # Algumas séries (ex.: meta Selic) trazem datas futuras: descartamos
    df = df[(df["data"] >= inicio) & (df["data"] <= fim)]
    return df[COLUNAS].dropna(subset=["valor"]).reset_index(drop=True)


def coletar(
    dir_bruto: Path | None = None,
    hoje: date | None = None,
    sessao: requests.Session | None = None,
) -> int:
    """Coleta incremental de todas as séries configuradas. Retorna linhas novas."""
    hoje = hoje or date.today()
    ultimos = armazenamento.ultimo_registro(FONTE, "serie_nome", "data", dir_bruto)
    primeiros = armazenamento.primeiro_registro(FONTE, "serie_nome", "data", dir_bruto)
    minimo = config.DATA_INICIO_PRECOS
    total = 0
    for codigo, nome in config.SERIES_SGS.items():
        inicio = armazenamento.inicio_incremental(
            ultimos.get(nome), config.SOBREPOSICAO_DIAS_DIARIO, minimo
        )
        df = coletar_serie(codigo, inicio, hoje, sessao=sessao)
        # Histórico anterior ao 1º registro (séries criadas antes de o início recuar)
        if armazenamento.falta_historico(primeiros.get(nome), minimo):
            fim_historico = pd.Timestamp(primeiros[nome]).date() - timedelta(days=1)
            df = pd.concat([coletar_serie(codigo, minimo, fim_historico, sessao=sessao), df],
                           ignore_index=True)
        n = armazenamento.salvar_incremental(
            df, FONTE, chaves=["serie_nome", "data"], col_tempo="data", dir_bruto=dir_bruto
        )
        log.info("SGS %s (%s): %s linhas baixadas, %s novas", codigo, nome, len(df), n)
        total += n
    return total
