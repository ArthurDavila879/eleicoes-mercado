"""Carga dos Parquet de ``data/bruto/`` e dos eventos no DuckDB (schema ``bruto``).

As tabelas são recriadas a cada carga a partir dos Parquet (fonte da verdade),
o que torna a carga idempotente. Fontes ainda sem arquivos geram tabelas vazias
com o esquema correto, para que o dbt sempre encontre as tabelas.
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import pandas as pd

from src import config
from src.eventos import validacao

log = logging.getLogger(__name__)

# Esquema de cada tabela bruta (usado quando ainda não há arquivos)
ESQUEMAS: dict[str, str] = {
    "bcb_sgs": "serie_codigo BIGINT, serie_nome VARCHAR, data TIMESTAMP, valor DOUBLE",
    "yahoo_diario": (
        "ticker VARCHAR, data TIMESTAMP, abertura DOUBLE, maxima DOUBLE, minima DOUBLE, "
        "fechamento DOUBLE, fechamento_ajustado DOUBLE, volume DOUBLE"
    ),
    "yahoo_horario": (
        "ticker VARCHAR, data_hora_utc TIMESTAMP, abertura DOUBLE, maxima DOUBLE, "
        "minima DOUBLE, fechamento DOUBLE, volume DOUBLE"
    ),
    "binance_horario": (
        "par VARCHAR, data_hora_utc TIMESTAMP, abertura DOUBLE, maxima DOUBLE, minima DOUBLE, "
        "fechamento DOUBLE, volume DOUBLE"
    ),
    "gdelt_diario": (
        "candidato VARCHAR, data TIMESTAMP, consulta VARCHAR, n_artigos BIGINT, "
        "total_monitorado BIGINT, tom_medio DOUBLE"
    ),
}


def carregar(
    caminho_db: Path | None = None,
    dir_bruto: Path | None = None,
    caminho_eventos: Path | None = None,
) -> dict[str, int]:
    """Recria as tabelas ``bruto.*``. Retorna o nº de linhas por tabela."""
    caminho_db = Path(caminho_db or config.CAMINHO_DUCKDB)
    dir_bruto = Path(dir_bruto or config.DIR_BRUTO)
    caminho_db.parent.mkdir(parents=True, exist_ok=True)
    caminho_eventos = Path(caminho_eventos or config.CAMINHO_EVENTOS)
    if caminho_eventos.exists():
        eventos = validacao.carregar(caminho_eventos)  # falha cedo se o CSV for inválido
    else:
        log.warning("Arquivo de eventos %s não encontrado: tabela vazia", caminho_eventos)
        eventos = pd.DataFrame(
            {"evento_id": pd.Series(dtype="int64"),
             **{c: pd.Series(dtype="str") for c in validacao.COLUNAS},
             "data_hora_utc": pd.Series(dtype="datetime64[us]")}
        )

    contagens: dict[str, int] = {}
    con = duckdb.connect(str(caminho_db))
    try:
        con.execute("CREATE SCHEMA IF NOT EXISTS bruto")
        for tabela, esquema in ESQUEMAS.items():
            colunas = [c.split()[0] for c in esquema.split(", ")]
            con.execute(f"CREATE OR REPLACE TABLE bruto.{tabela} ({esquema})")
            arquivos = sorted((dir_bruto / tabela).glob("*.parquet"))
            if arquivos:
                lista = ", ".join(f"'{a.as_posix()}'" for a in arquivos)
                con.execute(
                    f"INSERT INTO bruto.{tabela} BY NAME "
                    f"SELECT {', '.join(colunas)} FROM read_parquet([{lista}], union_by_name=true)"
                )
            contagens[tabela] = con.execute(f"SELECT count(*) FROM bruto.{tabela}").fetchall()[0][0]

        con.register("eventos_df", eventos)
        con.execute(
            "CREATE OR REPLACE TABLE bruto.eventos AS SELECT evento_id::INTEGER AS evento_id, "
            "data_hora, data_hora_utc::TIMESTAMP AS data_hora_utc, tipo, descricao, fonte_url "
            "FROM eventos_df"
        )
        contagens["eventos"] = len(eventos)
    finally:
        con.close()
    log.info("Carga no DuckDB (%s): %s", caminho_db, contagens)
    return contagens
