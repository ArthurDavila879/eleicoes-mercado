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


def inicio_historico(intervalo: str, hoje: date) -> date:
    """Data mais antiga a coletar: 01/01/2023 no diário; no horário, o limite do Yahoo."""
    if intervalo == "1d":
        return config.DATA_INICIO_PRECOS
    return max(config.DATA_INICIO_PRECOS, hoje - timedelta(days=config.HISTORICO_MAX_HORARIO_DIAS))


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
        primeiros = armazenamento.primeiro_registro(fonte, "ticker", col_tempo, dir_bruto)
        minimo = inicio_historico(intervalo, hoje)
        partes = []
        for ticker in tickers:
            if intervalo == "1h" and ticker in config.TICKERS_SO_DIARIO:
                continue
            tentativas += 1
            inicio = armazenamento.inicio_incremental(ultimos.get(ticker), sobreposicao, minimo)
            try:
                partes.append(coletar_ticker(ticker, inicio, fim, intervalo, baixar))
            except Exception as erro:  # um ticker com problema não derruba a coleta
                log.warning("Yahoo %s %s falhou: %s", ticker, intervalo, erro)
                falhas.append(f"{ticker}/{intervalo}")
            # Histórico anterior ao 1º registro (séries criadas antes de o início recuar)
            if armazenamento.falta_historico(primeiros.get(ticker), minimo):
                try:
                    partes.append(coletar_ticker(
                        ticker, minimo, pd.Timestamp(primeiros[ticker]).date(), intervalo, baixar))
                except Exception as erro:  # o histórico é tentado de novo na próxima coleta
                    log.warning("Yahoo histórico %s %s falhou: %s", ticker, intervalo, erro)
        partes = [p for p in partes if not p.empty]
        df = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()
        resultado[fonte] = armazenamento.salvar_incremental(
            df, fonte, chaves=["ticker", col_tempo], col_tempo=col_tempo, dir_bruto=dir_bruto
        )
        log.info("Yahoo %s: %s linhas baixadas, %s novas", intervalo, len(df), resultado[fonte])
    if falhas and len(falhas) == tentativas:
        raise RuntimeError("Todas as coletas do Yahoo falharam: " + ", ".join(falhas))
    return resultado
