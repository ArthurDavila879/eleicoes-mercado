"""Mescla Parquet coletados em outro diretório aos de ``data/bruto``.

Uso na CI: ``python -m src.ingestao.mesclar <dir_coletado>``. O git não mescla
arquivos binários, então quando o ``main`` recebe dados novos durante a coleta, a
CI volta para o ``main`` atualizado e reaplica a sua coleta por aqui, unindo as
linhas pela chave de cada fonte (a mesma de ``salvar_incremental``).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src.ingestao import armazenamento, bcb, binance, gdelt, yahoo

# fonte -> (chaves, coluna de tempo)
FONTES: dict[str, tuple[list[str], str]] = {
    bcb.FONTE: (["serie_nome", "data"], "data"),
    gdelt.FONTE: (["candidato", "data"], "data"),
    yahoo.FONTE_DIARIO: (["ticker", "data"], "data"),
    yahoo.FONTE_HORARIO: (["ticker", "data_hora_utc"], "data_hora_utc"),
    binance.FONTE: (["par", "data_hora_utc"], "data_hora_utc"),
}


def mesclar(origem: Path, dir_bruto: Path | None = None) -> dict[str, int]:
    """Une os Parquet de ``origem`` aos de ``dir_bruto``. Retorna linhas novas por fonte."""
    resultado: dict[str, int] = {}
    for fonte, (chaves, col_tempo) in FONTES.items():
        df = armazenamento.ler_fonte(fonte, origem)
        if df.empty:
            continue
        resultado[fonte] = armazenamento.salvar_incremental(df, fonte, chaves, col_tempo, dir_bruto)
    return resultado


def main() -> None:
    parser = argparse.ArgumentParser(description="Mescla Parquet coletados aos de data/bruto")
    parser.add_argument("origem", type=Path, help="diretório com <fonte>/<AAAA-MM>.parquet")
    args = parser.parse_args()
    print("Linhas novas após mesclar:", mesclar(args.origem))


if __name__ == "__main__":
    main()
