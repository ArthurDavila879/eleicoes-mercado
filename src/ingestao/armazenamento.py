"""Armazenamento em Parquet particionado por mês, incremental e idempotente.

Cada fonte fica em ``data/bruto/<fonte>/<AAAA-MM>.parquet``. Ao salvar, os novos
registros são mesclados com os existentes e duplicatas (pela chave) são removidas,
mantendo a versão mais recente. Salvar duas vezes os mesmos dados não altera nada.
Particionar por mês faz com que a coleta horária só reescreva o arquivo do mês corrente.
"""

from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from src import config


def _dir_fonte(fonte: str, dir_bruto: Path | None) -> Path:
    return Path(dir_bruto or config.DIR_BRUTO) / fonte


def _normalizar_tempo(df: pd.DataFrame, col_tempo: str) -> pd.DataFrame:
    """Padroniza a coluna de tempo como datetime64[us] sem fuso (UTC, quando horária).

    Garante que registros novos e antigos sejam comparáveis na deduplicação.
    """
    df = df.copy()
    tempo = pd.to_datetime(df[col_tempo])
    if tempo.dt.tz is not None:
        tempo = tempo.dt.tz_convert("UTC").dt.tz_localize(None)
    df[col_tempo] = tempo.astype("datetime64[us]")
    return df


def ler_fonte(fonte: str, dir_bruto: Path | None = None) -> pd.DataFrame:
    """Lê todos os arquivos Parquet de uma fonte (DataFrame vazio se não houver)."""
    arquivos = sorted(_dir_fonte(fonte, dir_bruto).glob("*.parquet"))
    if not arquivos:
        return pd.DataFrame()
    return pd.concat([pd.read_parquet(a) for a in arquivos], ignore_index=True)


def salvar_incremental(
    df: pd.DataFrame,
    fonte: str,
    chaves: list[str],
    col_tempo: str,
    dir_bruto: Path | None = None,
) -> int:
    """Mescla ``df`` aos Parquet da fonte. Retorna o nº de linhas novas ou alteradas."""
    if df.empty:
        return 0
    destino = _dir_fonte(fonte, dir_bruto)
    destino.mkdir(parents=True, exist_ok=True)

    df = _normalizar_tempo(df, col_tempo)
    df = df.drop_duplicates(subset=chaves, keep="last")
    meses = pd.to_datetime(df[col_tempo]).dt.strftime("%Y-%m")
    alteradas = 0
    for mes, parte in df.groupby(meses):
        arquivo = destino / f"{mes}.parquet"
        if arquivo.exists():
            antigo = _normalizar_tempo(pd.read_parquet(arquivo), col_tempo)
            combinado = pd.concat([antigo, parte], ignore_index=True)
            combinado = combinado.drop_duplicates(subset=chaves, keep="last")
            # Conta linhas novas/alteradas comparando com o conteúdo anterior
            juncao = combinado.merge(antigo, how="left", indicator=True)
            alteradas_mes = int((juncao["_merge"] == "left_only").sum())
        else:
            combinado = parte
            alteradas_mes = len(parte)
        if alteradas_mes == 0:
            continue  # nada mudou: não reescreve o arquivo (idempotência)
        combinado = combinado.sort_values(chaves).reset_index(drop=True)
        temporario = arquivo.with_suffix(".parquet.tmp")
        combinado.to_parquet(temporario, index=False)
        os.replace(temporario, arquivo)  # escrita atômica
        alteradas += alteradas_mes
    return alteradas


def ultimo_registro(
    fonte: str, col_grupo: str, col_tempo: str, dir_bruto: Path | None = None
) -> dict[str, datetime]:
    """Último instante coletado por série/ativo (ex.: {'PETR4.SA': Timestamp(...)})."""
    df = ler_fonte(fonte, dir_bruto)
    if df.empty:
        return {}
    ultimos = pd.to_datetime(df[col_tempo]).groupby(df[col_grupo]).max()
    return {str(k): v.to_pydatetime() for k, v in ultimos.items()}


def primeiro_registro(
    fonte: str, col_grupo: str, col_tempo: str, dir_bruto: Path | None = None
) -> dict[str, datetime]:
    """Primeiro instante coletado por série/ativo."""
    df = ler_fonte(fonte, dir_bruto)
    if df.empty:
        return {}
    primeiros = pd.to_datetime(df[col_tempo]).groupby(df[col_grupo]).min()
    return {str(k): v.to_pydatetime() for k, v in primeiros.items()}


def falta_historico(primeiro: datetime | None, minimo: date) -> bool:
    """True se a série já existe mas começa depois de ``minimo`` (+ tolerância)."""
    if primeiro is None:
        return False  # série nova: a coleta incremental já começa em ``minimo``
    limite = minimo + pd.Timedelta(days=config.TOLERANCIA_HISTORICO_DIAS)
    return pd.Timestamp(primeiro).date() > limite


def inicio_incremental(
    ultimo: datetime | None, sobreposicao_dias: int, minimo: date | None = None
) -> date:
    """Data de início da próxima coleta: último registro menos a sobreposição."""
    minimo = minimo or config.DATA_INICIO
    if ultimo is None:
        return minimo
    inicio = (pd.Timestamp(ultimo) - pd.Timedelta(days=sobreposicao_dias)).date()
    return max(inicio, minimo)
