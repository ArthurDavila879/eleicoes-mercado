"""Coleta de cotações do Yahoo Finance (yfinance), diárias e de hora em hora.

- Diário: ``data`` é a data do pregão no fuso da bolsa/mercado do ativo.
- Horário: ``data_hora_utc`` é o INÍCIO da barra de 1h, em UTC (sem fuso).
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Callable

import pandas as pd
import yfinance as yf

from src import config
from src.ingestao import armazenamento

log = logging.getLogger(__name__)

FONTE_DIARIO = "yahoo_diario"
FONTE_HORARIO = "yahoo_horario"

COLUNAS_DIARIO = [
    "ticker", "data", "abertura", "maxima", "minima", "fechamento",
    "fechamento_ajustado", "volume",
]
COLUNAS_HORARIO = [
    "ticker", "data_hora_utc", "abertura", "maxima", "minima", "fechamento", "volume",
]

RENOMEAR = {
    "Open": "abertura", "High": "maxima", "Low": "minima", "Close": "fechamento",
    "Adj Close": "fechamento_ajustado", "Volume": "volume",
}


def _historico_padrao(ticker: str, inicio: date, fim: date, intervalo: str) -> pd.DataFrame:
    return yf.Ticker(ticker).history(
        start=inicio.isoformat(), end=fim.isoformat(), interval=intervalo,
        auto_adjust=False, actions=False,
    )


def coletar_ticker(
    ticker: str,
    inicio: date,
    fim: date,
    intervalo: str,
    baixar: Callable[[str, date, date, str], pd.DataFrame] = _historico_padrao,
) -> pd.DataFrame:
    """Baixa um ticker. ``fim`` é exclusivo (convenção do yfinance)."""
    bruto = baixar(ticker, inicio, fim, intervalo)
    colunas = COLUNAS_DIARIO if intervalo == "1d" else COLUNAS_HORARIO
    if bruto is None or bruto.empty:
        return pd.DataFrame(columns=colunas)

    df = bruto.rename(columns=RENOMEAR).copy()
    indice = pd.DatetimeIndex(df.index)
    if intervalo == "1d":
        # Data do pregão no fuso do próprio mercado
        df["data"] = (indice.tz_localize(None) if indice.tz is not None else indice).normalize()
        if "fechamento_ajustado" not in df:
            df["fechamento_ajustado"] = df["fechamento"]
    else:
        if indice.tz is None:
            indice = indice.tz_localize("UTC")
        df["data_hora_utc"] = indice.tz_convert("UTC").tz_localize(None)
        # Durante o pregão o yfinance pode anexar uma linha "ao vivo" fora da hora cheia
        # (ex.: 11:37); só barras que começam na hora cheia são mantidas.
        df = df[(df["data_hora_utc"].dt.minute == 0) & (df["data_hora_utc"].dt.second == 0)]
    df["ticker"] = ticker
    df = df.dropna(subset=["fechamento"])
    df = df[df["fechamento"] > 0]
    return df[colunas].reset_index(drop=True)


def coletar(
    dir_bruto: Path | None = None,
    hoje: date | None = None,
    baixar: Callable[[str, date, date, str], pd.DataFrame] = _historico_padrao,
    tickers: list[str] | None = None,
) -> dict[str, int]:
    """Coleta incremental diária e horária de todos os tickers. Retorna linhas novas."""
    hoje = hoje or date.today()
    fim = hoje + timedelta(days=1)  # yfinance trata ``end`` como exclusivo
    tickers = tickers or config.TICKERS_YAHOO
    resultado: dict[str, int] = {}
    falhas: list[str] = []
    tentativas = 0
    for fonte, intervalo, col_tempo, sobreposicao in [
        (FONTE_DIARIO, "1d", "data", config.SOBREPOSICAO_DIAS_DIARIO),
        (FONTE_HORARIO, "1h", "data_hora_utc", config.SOBREPOSICAO_DIAS_HORARIO),
    ]:
        ultimos = armazenamento.ultimo_registro(fonte, "ticker", col_tempo, dir_bruto)
        partes = []
        for ticker in tickers:
            if intervalo == "1h" and ticker in config.TICKERS_SO_DIARIO:
                continue
            tentativas += 1
            inicio = armazenamento.inicio_incremental(ultimos.get(ticker), sobreposicao)
            try:
                partes.append(coletar_ticker(ticker, inicio, fim, intervalo, baixar))
            except Exception as erro:  # um ticker com problema não derruba a coleta
                log.warning("Yahoo %s %s falhou: %s", ticker, intervalo, erro)
                falhas.append(f"{ticker}/{intervalo}")
        partes = [p for p in partes if not p.empty]
        df = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()
        resultado[fonte] = armazenamento.salvar_incremental(
            df, fonte, chaves=["ticker", col_tempo], col_tempo=col_tempo, dir_bruto=dir_bruto
        )
        log.info("Yahoo %s: %s linhas baixadas, %s novas", intervalo, len(df), resultado[fonte])
    if falhas and len(falhas) == tentativas:
        raise RuntimeError("Todas as coletas do Yahoo falharam: " + ", ".join(falhas))
    return resultado
