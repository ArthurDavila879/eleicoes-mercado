"""Coleta de barras de 1h de bitcoin na Binance (BTCBRL e BTCUSDT), para o dólar implícito.

O Yahoo Finance não tem cotação BTC-BRL; a Binance tem os dois pares na mesma corretora
(``USD/BRL implícito = BTCBRL / BTCUSDT``, com a USDT como aproximação do dólar), 24 horas
por dia, inclusive nos fins de semana. Usa o endpoint público de dados de mercado
(sem autenticação): https://data-api.binance.vision/api/v3/klines

``data_hora_utc`` é o INÍCIO da barra de 1h, em UTC (sem fuso); a barra fecha 1h depois.
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

from src import config
from src.ingestao import armazenamento

log = logging.getLogger(__name__)

FONTE = "binance_horario"
URL_KLINES = "https://data-api.binance.vision/api/v3/klines"
COLUNAS = ["par", "data_hora_utc", "abertura", "maxima", "minima", "fechamento", "volume"]
LIMITE_POR_REQUISICAO = 1000  # máximo da API
UMA_HORA_MS = 3_600_000


def _ms(instante: datetime) -> int:
    return int(instante.replace(tzinfo=timezone.utc).timestamp() * 1000)


def coletar_par(
    par: str,
    inicio: datetime,
    fim: datetime,
    sessao: requests.Session | None = None,
    tentativas: int = 3,
) -> pd.DataFrame:
    """Barras de 1h de ``par`` que começam em [inicio, fim), paginando de 1000 em 1000."""
    sessao = sessao or requests.Session()
    linhas: list[list] = []
    cursor, limite = _ms(inicio), _ms(fim)
    while cursor < limite:
        params = {"symbol": par, "interval": "1h", "startTime": cursor, "endTime": limite - 1,
                  "limit": LIMITE_POR_REQUISICAO}
        for tentativa in range(1, tentativas + 1):
            try:
                resp = sessao.get(URL_KLINES, params=params, timeout=60)
                resp.raise_for_status()
                lote = resp.json()
                break
            except (requests.RequestException, ValueError, RuntimeError) as erro:
                log.warning("Binance %s: %s (tentativa %s)", par, erro, tentativa)
                if tentativa == tentativas:
                    raise
                time.sleep(5 * tentativa)
        if not lote:
            break
        linhas.extend(lote)
        cursor = int(lote[-1][0]) + UMA_HORA_MS
        if len(lote) < LIMITE_POR_REQUISICAO:
            break
    if not linhas:
        return pd.DataFrame(columns=COLUNAS)
    df = pd.DataFrame([k[:6] for k in linhas],
                      columns=["data_hora_utc", "abertura", "maxima", "minima", "fechamento", "volume"])
    df["data_hora_utc"] = pd.to_datetime(df["data_hora_utc"].astype("int64"), unit="ms")
    for col in COLUNAS[2:]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["par"] = par
    df = df.dropna(subset=["fechamento"])
    return df[df["fechamento"] > 0][COLUNAS].reset_index(drop=True)


def coletar(
    dir_bruto: Path | None = None,
    hoje: date | None = None,
    sessao: requests.Session | None = None,
) -> int:
    """Coleta incremental dos pares configurados. Retorna linhas novas."""
    hoje = hoje or date.today()
    fim = datetime.combine(hoje + timedelta(days=1), datetime.min.time())
    ultimos = armazenamento.ultimo_registro(FONTE, "par", "data_hora_utc", dir_bruto)
    total, falhas = 0, []
    for par in config.PARES_BINANCE:
        inicio = armazenamento.inicio_incremental(
            ultimos.get(par), config.SOBREPOSICAO_DIAS_HORARIO, config.DATA_INICIO_CRIPTO)
        try:
            df = coletar_par(par, datetime.combine(inicio, datetime.min.time()), fim, sessao)
        except Exception as erro:  # um par com problema não derruba o outro
            log.warning("Binance %s falhou: %s", par, erro)
            falhas.append(par)
            continue
        n = armazenamento.salvar_incremental(
            df, FONTE, chaves=["par", "data_hora_utc"], col_tempo="data_hora_utc", dir_bruto=dir_bruto)
        log.info("Binance %s: %s barras baixadas, %s novas", par, len(df), n)
        total += n
    if falhas and len(falhas) == len(config.PARES_BINANCE):
        raise RuntimeError("Todas as coletas da Binance falharam: " + ", ".join(falhas))
    return total
