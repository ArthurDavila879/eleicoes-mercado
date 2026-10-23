"""Coleta incremental: ``python -m src.ingestao [--fontes bcb_sgs yahoo gdelt] [--carregar]``."""

from __future__ import annotations

import argparse
import logging
import sys
import warnings

from src.ingestao import FONTES, carga, coletar_tudo


def configurar_saida() -> None:
    """Saída em UTF-8 e sem avisos de depreciação internos das bibliotecas."""
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8")
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", module="yfinance")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Coleta incremental das fontes de dados")
    parser.add_argument("--fontes", nargs="+", choices=FONTES, default=list(FONTES),
                        help="fontes a coletar (padrão: todas)")
    parser.add_argument("--carregar", action="store_true", help="também carrega no DuckDB")
    args = parser.parse_args()
    configurar_saida()

    resultado = coletar_tudo(fontes=args.fontes)
    print("Linhas novas por fonte:", resultado)
    if args.carregar:
        print("Linhas no DuckDB:", carga.carregar())


if __name__ == "__main__":
    main()
