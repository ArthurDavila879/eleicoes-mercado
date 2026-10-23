"""Pipeline completo: coleta → validação dos eventos → carga no DuckDB → dbt build.

Uso: ``python -m src.pipeline [--sem-coleta] [--sem-dbt]``
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from src import config
from src.ingestao import carga, coletar_tudo
from src.ingestao.__main__ import configurar_saida

log = logging.getLogger("pipeline")


def rodar_dbt(comando: str = "build", argumentos_extras: list[str] | None = None) -> bool:
    """Executa o dbt no projeto ``dbt/`` usando o mesmo arquivo DuckDB da carga."""
    from dbt.cli.main import dbtRunner

    os.environ.setdefault("DUCKDB_PATH", str(config.CAMINHO_DUCKDB))
    resultado = dbtRunner().invoke(
        [comando, "--project-dir", str(config.DIR_DBT), "--profiles-dir", str(config.DIR_DBT)]
        + (argumentos_extras or [])
    )
    return bool(resultado.success)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sem-coleta", action="store_true", help="usa só os Parquet existentes")
    parser.add_argument("--sem-dbt", action="store_true", help="não roda o dbt build")
    args = parser.parse_args()
    configurar_saida()

    if not args.sem_coleta:
        log.info("Coleta: %s", coletar_tudo())
    log.info("Carga: %s", carga.carregar())
    if not args.sem_dbt and not rodar_dbt("build"):
        log.error("dbt build falhou")
        sys.exit(1)
    log.info("Pipeline concluído")


if __name__ == "__main__":
    main()
