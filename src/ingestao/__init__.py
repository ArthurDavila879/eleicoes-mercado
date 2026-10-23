"""Ingestão de dados: BCB/SGS, Yahoo Finance e GDELT → Parquet → DuckDB."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

log = logging.getLogger(__name__)


def coletar_tudo(dir_bruto: Path | None = None, hoje: date | None = None) -> dict[str, object]:
    """Roda todas as coletas incrementais. Uma fonte com erro não impede as demais.

    Retorna, por fonte, o nº de linhas novas ou a mensagem de erro.
    Levanta ``RuntimeError`` se TODAS as fontes falharem.
    """
    from src.ingestao import bcb, gdelt, yahoo

    resultado: dict[str, object] = {}
    coletores = {"bcb_sgs": bcb.coletar, "yahoo": yahoo.coletar, "gdelt": gdelt.coletar}
    for nome, coletor in coletores.items():
        try:
            resultado[nome] = coletor(dir_bruto=dir_bruto, hoje=hoje)
        except Exception as erro:
            log.error("Coleta %s falhou: %s", nome, erro)
            resultado[nome] = f"ERRO: {erro}"
    if all(isinstance(v, str) and v.startswith("ERRO") for v in resultado.values()):
        raise RuntimeError(f"Todas as coletas falharam: {resultado}")
    return resultado
