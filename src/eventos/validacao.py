"""Validação do arquivo de eventos (``data/eventos.csv``).

Formato esperado (UTF-8, separador vírgula):
- ``data_hora``: ISO 8601 com fuso explícito, ex.: ``2026-10-04T17:00:00-03:00``
- ``tipo``: debate, pesquisa, resultado, declaracao ou outro
- ``descricao``: texto não vazio
- ``fonte_url``: URL http(s) da fonte que comprova a data/hora
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

from src import config

COLUNAS = ["data_hora", "tipo", "descricao", "fonte_url"]
TIPOS_VALIDOS = {"debate", "pesquisa", "resultado", "declaracao", "outro"}
RE_DATA_HORA = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?([+-]\d{2}:\d{2}|Z)$")
RE_URL = re.compile(r"^https?://[^\s/$.?#].[^\s]*$")


class EventosInvalidos(ValueError):
    """O arquivo de eventos não segue o formato esperado."""


def validar(df: pd.DataFrame) -> list[str]:
    """Retorna a lista de erros encontrados (vazia se o arquivo for válido)."""
    erros: list[str] = []
    if list(df.columns) != COLUNAS:
        return [f"colunas devem ser exatamente {COLUNAS}; encontradas {list(df.columns)}"]
    for i, linha in df.iterrows():
        n = i + 2  # nº da linha no arquivo (cabeçalho é a linha 1)
        data_hora = str(linha["data_hora"]).strip() if pd.notna(linha["data_hora"]) else ""
        if not RE_DATA_HORA.match(data_hora):
            erros.append(f"linha {n}: data_hora '{data_hora}' não é ISO 8601 com fuso")
        else:
            try:
                pd.Timestamp(data_hora)
            except ValueError:
                erros.append(f"linha {n}: data_hora '{data_hora}' é uma data inexistente")
        if linha["tipo"] not in TIPOS_VALIDOS:
            erros.append(f"linha {n}: tipo '{linha['tipo']}' fora de {sorted(TIPOS_VALIDOS)}")
        if pd.isna(linha["descricao"]) or not str(linha["descricao"]).strip():
            erros.append(f"linha {n}: descricao vazia")
        if pd.isna(linha["fonte_url"]) or not RE_URL.match(str(linha["fonte_url"]).strip()):
            erros.append(f"linha {n}: fonte_url '{linha['fonte_url']}' não é uma URL http(s)")
    if not erros:
        duplicadas = df.duplicated(subset=["data_hora", "tipo", "descricao"])
        for i in df.index[duplicadas]:
            erros.append(f"linha {i + 2}: evento duplicado")
    return erros


def carregar(caminho: Path | None = None) -> pd.DataFrame:
    """Lê e valida o CSV. Devolve DataFrame com ``data_hora_utc`` (UTC, sem fuso)."""
    caminho = Path(caminho or config.CAMINHO_EVENTOS)
    df = pd.read_csv(caminho, dtype=str, keep_default_na=False, na_values=[""])
    erros = validar(df)
    if erros:
        raise EventosInvalidos(f"{caminho}:\n  " + "\n  ".join(erros))
    df = df.copy()
    instantes = df["data_hora"].map(lambda v: pd.Timestamp(v).tz_convert("UTC"))
    df["data_hora_utc"] = pd.to_datetime(instantes).dt.tz_localize(None).astype("datetime64[us]")
    # evento_id = ordem da linha no arquivo: acrescentar eventos (inclusive mais antigos) no
    # fim não muda os ids existentes, citados no README e no PRE_REGISTRO.md
    df.insert(0, "evento_id", range(1, len(df) + 1))
    return df


if __name__ == "__main__":
    try:
        eventos = carregar(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
    except EventosInvalidos as erro:
        print(f"ERRO: {erro}")
        sys.exit(1)
    print(f"OK: {len(eventos)} eventos válidos")
