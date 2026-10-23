"""Ingestão de dados: BCB/SGS, Yahoo Finance, GDELT e Binance → Parquet → DuckDB."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

log = logging.getLogger(__name__)


FONTES = ("bcb_sgs", "yahoo", "gdelt", "binance")


def coletar_tudo(
    dir_bruto: Path | None = None,
    hoje: date | None = None,
    fontes: tuple[str, ...] | list[str] = FONTES,
) -> dict[str, object]:
    """Roda as coletas incrementais das ``fontes`` pedidas (todas, por padrão).
    Uma fonte com erro não impede as demais.

    Retorna, por fonte, o nº de linhas novas ou a mensagem de erro.
    Levanta ``RuntimeError`` se TODAS as fontes falharem.
    """
    from src.ingestao import bcb, binance, gdelt, yahoo

    resultado: dict[str, object] = {}
    coletores = {"bcb_sgs": bcb.coletar, "yahoo": yahoo.coletar, "gdelt": gdelt.coletar,
                 "binance": binance.coletar}
    desconhecidas = set(fontes) - set(coletores)
    if desconhecidas:
        raise ValueError(f"Fontes desconhecidas: {sorted(desconhecidas)}")
    for nome, coletor in coletores.items():
        if nome not in fontes:
            continue
        try:
            resultado[nome] = coletor(dir_bruto=dir_bruto, hoje=hoje)
        except Exception as erro:
            log.error("Coleta %s falhou: %s", nome, erro)
            resultado[nome] = f"ERRO: {erro}"
    if all(isinstance(v, str) and v.startswith("ERRO") for v in resultado.values()):
        raise RuntimeError(f"Todas as coletas falharam: {resultado}")
    return resultado
