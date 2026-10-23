"""Garante que o DuckDB do dashboard exista e esteja atualizado em relação aos Parquet.

No Streamlit Community Cloud não há etapa de build: o app chama ``garantir_banco`` na
inicialização. O banco é reconstruído (carga + ``dbt build``, sem coleta) só quando falta ou
quando a impressão digital das entradas mudou — Parquet, eventos, projeto dbt e código Python.
O pipeline grava a impressão ao terminar, então um banco feito por ``python -m src.pipeline``
não é refeito pelo app.

A construção roda num subprocesso: o dbt-duckdb mantém a conexão de escrita aberta no processo
que o executa, e o app precisa abrir o mesmo arquivo em modo somente leitura.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable

from src import config

log = logging.getLogger(__name__)

# Entradas que, se mudarem, exigem reconstruir o banco
PADROES_ENTRADA = [
    ("data/bruto", "**/*.parquet"),
    ("data", "eventos.csv"),
    ("dbt", "dbt_project.yml"),
    ("dbt", "profiles.yml"),
    ("dbt/models", "**/*"),
    ("dbt/macros", "**/*"),
    ("dbt/seeds", "**/*"),
    ("dbt/tests", "**/*"),
    ("src", "**/*.py"),
]


def caminho_impressao(caminho_db: Path) -> Path:
    return caminho_db.with_name(caminho_db.name + ".impressao.json")


def impressao_digital(raiz: Path | None = None, dir_bruto: Path | None = None) -> str:
    """SHA-256 do conteúdo de todas as entradas do banco (ordem estável)."""
    raiz = Path(raiz or config.RAIZ)
    h = hashlib.sha256()
    for base, padrao in PADROES_ENTRADA:
        pasta = Path(dir_bruto) if (dir_bruto and base == "data/bruto") else raiz / base
        for arquivo in sorted(p for p in pasta.glob(padrao) if p.is_file()):
            if "__pycache__" in arquivo.parts:
                continue
            h.update(arquivo.relative_to(pasta).as_posix().encode())
            h.update(arquivo.read_bytes())
    return h.hexdigest()


def gravar_impressao(caminho_db: Path | None = None, impressao: str | None = None) -> None:
    caminho_db = Path(caminho_db or config.CAMINHO_DUCKDB)
    caminho_impressao(caminho_db).write_text(
        json.dumps({"impressao": impressao or impressao_digital()}), encoding="utf-8")


def banco_atualizado(caminho_db: Path | None = None, impressao: str | None = None) -> bool:
    caminho_db = Path(caminho_db or config.CAMINHO_DUCKDB)
    arquivo = caminho_impressao(caminho_db)
    if not caminho_db.exists() or not arquivo.exists():
        return False
    try:
        gravada = json.loads(arquivo.read_text(encoding="utf-8"))["impressao"]
    except (ValueError, KeyError):
        return False
    return gravada == (impressao or impressao_digital())


def _construir_subprocesso(caminho_db: Path) -> bool:
    ambiente = {**os.environ, "DUCKDB_PATH": str(caminho_db)}
    resultado = subprocess.run(
        [sys.executable, "-m", "src.pipeline", "--sem-coleta"],
        cwd=config.RAIZ, env=ambiente, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=1800,
    )
    if resultado.returncode != 0:
        log.error("Construção do banco falhou:\n%s", (resultado.stdout + resultado.stderr)[-4000:])
    return resultado.returncode == 0


def garantir_banco(
    caminho_db: Path | None = None,
    construir: Callable[[Path], bool] = _construir_subprocesso,
) -> str:
    """Reconstrói o banco se estiver ausente ou desatualizado.

    Retorna ``"atual"`` (nada a fazer), ``"construido"`` ou ``"falhou"``.
    """
    caminho_db = Path(caminho_db or config.CAMINHO_DUCKDB)
    impressao = impressao_digital()
    if banco_atualizado(caminho_db, impressao):
        return "atual"
    log.info("Banco ausente ou desatualizado: reconstruindo %s a partir dos Parquet", caminho_db)
    if not construir(caminho_db):
        return "falhou"
    # Grava a impressão calculada ANTES da construção: se as entradas mudarem durante a
    # construção, a próxima verificação reconstrói de novo
    gravar_impressao(caminho_db, impressao)
    return "construido"
