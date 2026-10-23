"""Coleta do GDELT DOC 2.0: volume diário de notícias e tom médio por candidato.

A MESMA consulta-base (``config.CONSULTA_BASE_GDELT``) é aplicada a cada candidato,
com os mesmos parâmetros, para que as séries sejam comparáveis e o tratamento neutro.

Documentação: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
- ``mode=timelinevolraw``: nº de artigos que casam com a consulta (``value``) e o total
  de artigos monitorados no período (``norm``).
- ``mode=timelinetone``: tom médio dos artigos que casam com a consulta.
A API só pesquisa os últimos ~3 meses e pede no máximo 1 requisição a cada 5 segundos;
na prática recusa chamadas mesmo nesse ritmo (limite por IP, instável), por isso o
intervalo é folgado, o recuo após recusa é longo e a falha de um candidato não
impede a coleta dos demais.
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

from src import config
from src.ingestao import armazenamento

log = logging.getLogger(__name__)

FONTE = "gdelt_diario"
URL_DOC = "https://api.gdeltproject.org/api/v2/doc/doc"
COLUNAS = ["candidato", "data", "consulta", "n_artigos", "total_monitorado", "tom_medio"]
INTERVALO_MIN_SEGUNDOS = 10.0
RECUO_INICIAL_SEGUNDOS = 30.0  # espera após a 1ª recusa; dobra a cada nova tentativa


class LimiteRequisicoes(RuntimeError):
    """GDELT recusou a requisição por excesso de chamadas."""


def montar_consulta(candidato: str) -> str:
    """Aplica a consulta-base ao nome. Regra única para todos os candidatos: nomes com
    mais de uma palavra viram frase exata entre aspas; nome de uma palavra só fica sem
    aspas (o GDELT recusa frases curtas como ``"Lula"``, e uma palavra solta já é
    buscada como palavra inteira)."""
    termo = f'"{candidato}"' if " " in candidato.strip() else candidato.strip()
    return config.CONSULTA_BASE_GDELT.format(termo=termo)


def _pedir_timeline(
    sessao: requests.Session,
    consulta: str,
    modo: str,
    inicio: date,
    fim: date,
    tentativas: int,
    recuo: float,
) -> list[dict]:
    params = {
        "query": consulta,
        "mode": modo,
        "format": "json",
        "timelineres": "day",
        "startdatetime": inicio.strftime("%Y%m%d000000"),
        "enddatetime": fim.strftime("%Y%m%d235959"),
    }
    for tentativa in range(1, tentativas + 1):
        if tentativa > 1:
            time.sleep(recuo * 2 ** (tentativa - 2))  # recuo exponencial: 30 s, 60 s, 120 s...
        try:
            resp = sessao.get(URL_DOC, params=params, timeout=60,
                              headers={"User-Agent": "eleicoes-mercado/1.0 (pesquisa academica)"})
        except requests.RequestException as erro:
            log.warning("GDELT %s: %s (tentativa %s)", modo, erro, tentativa)
            continue
        texto = resp.text.strip()
        if resp.status_code == 200 and texto.startswith("{"):
            dados = resp.json()
            timeline = dados.get("timeline") or []
            return timeline[0].get("data", []) if timeline else []
        if resp.status_code == 200 and not texto:
            return []  # consulta sem resultados
        log.warning("GDELT %s (%s): resposta inválida/limite (tentativa %s): %s",
                    modo, consulta, tentativa, texto[:120])
    raise LimiteRequisicoes(f"GDELT não respondeu JSON para {modo} {consulta!r}")


def _converter_data(valor: str) -> datetime:
    # Formato da API: "20261004T000000Z"
    return datetime.strptime(valor[:8], "%Y%m%d")


def coletar_candidato(
    candidato: str,
    inicio: date,
    fim: date,
    sessao: requests.Session | None = None,
    tentativas: int = 4,
    espera: float = INTERVALO_MIN_SEGUNDOS,
    recuo: float = RECUO_INICIAL_SEGUNDOS,
) -> pd.DataFrame:
    """Volume e tom diários de um candidato entre ``inicio`` e ``fim``."""
    sessao = sessao or requests.Session()
    consulta = montar_consulta(candidato)
    volume = _pedir_timeline(sessao, consulta, "timelinevolraw", inicio, fim, tentativas, recuo)
    time.sleep(espera)  # respeita o limite de 1 requisição a cada 5 s
    try:
        tom = _pedir_timeline(sessao, consulta, "timelinetone", inicio, fim, tentativas, recuo)
    except LimiteRequisicoes:
        if not volume:
            raise
        # Guarda o volume; o tom fica nulo e é preenchido pela sobreposição da próxima coleta
        log.warning("GDELT %s: tom indisponível nesta coleta; salvando só o volume", candidato)
        tom = []

    df_vol = pd.DataFrame(
        {"data": [_converter_data(p["date"]) for p in volume],
         "n_artigos": [p.get("value") for p in volume],
         "total_monitorado": [p.get("norm") for p in volume]}
    )
    df_tom = pd.DataFrame(
        {"data": [_converter_data(p["date"]) for p in tom],
         "tom_medio": [p.get("value") for p in tom]}
    )
    if df_vol.empty and df_tom.empty:
        return pd.DataFrame(columns=COLUNAS)
    df = df_vol.merge(df_tom, on="data", how="outer") if not df_vol.empty else df_tom
    for coluna in ["n_artigos", "total_monitorado", "tom_medio"]:
        if coluna not in df:
            df[coluna] = pd.NA
    df["candidato"] = candidato
    df["consulta"] = consulta
    df["n_artigos"] = pd.to_numeric(df["n_artigos"]).astype("Int64")
    df["total_monitorado"] = pd.to_numeric(df["total_monitorado"]).astype("Int64")
    df["tom_medio"] = pd.to_numeric(df["tom_medio"]).astype("float64")
    df = df[(df["data"].dt.date >= inicio) & (df["data"].dt.date <= fim)]
    return df[COLUNAS].reset_index(drop=True)


def _preservar_tom_existente(df: pd.DataFrame, dir_bruto: Path | None) -> pd.DataFrame:
    """Se o tom veio nulo nesta coleta, mantém o tom já salvo para o mesmo dia."""
    if df.empty or df["tom_medio"].notna().all():
        return df
    existente = armazenamento.ler_fonte(FONTE, dir_bruto)
    if existente.empty:
        return df
    existente = existente[["candidato", "data", "tom_medio"]].rename(columns={"tom_medio": "_tom"})
    existente["data"] = pd.to_datetime(existente["data"])
    df = df.assign(data=pd.to_datetime(df["data"])).merge(existente, on=["candidato", "data"], how="left")
    df["tom_medio"] = df["tom_medio"].fillna(df.pop("_tom"))
    return df[COLUNAS]


def coletar(
    dir_bruto: Path | None = None,
    hoje: date | None = None,
    sessao: requests.Session | None = None,
    espera: float = INTERVALO_MIN_SEGUNDOS,
) -> int:
    """Coleta incremental para todos os candidatos do 2º turno. Retorna linhas novas.

    Um candidato que falhar (ex.: limite de requisições) é registrado e pulado; a
    sobreposição da próxima coleta recupera os dias perdidos. Só levanta erro se todos
    os candidatos falharem.
    """
    hoje = hoje or date.today()
    minimo = max(config.DATA_INICIO, hoje - timedelta(days=config.JANELA_MAX_GDELT_DIAS))
    ultimos = armazenamento.ultimo_registro(FONTE, "candidato", "data", dir_bruto)
    sessao = sessao or requests.Session()
    total = 0
    falhas: dict[str, str] = {}
    for i, candidato in enumerate(config.CANDIDATOS_2_TURNO):
        if i:
            time.sleep(espera)
        inicio = armazenamento.inicio_incremental(
            ultimos.get(candidato), config.SOBREPOSICAO_DIAS_GDELT, minimo=minimo
        )
        try:
            df = coletar_candidato(candidato, inicio, hoje, sessao=sessao, espera=espera)
        except LimiteRequisicoes as erro:
            log.error("GDELT %s: coleta pulada nesta rodada: %s", candidato, erro)
            falhas[candidato] = str(erro)
            continue
        df = _preservar_tom_existente(df, dir_bruto)
        n = armazenamento.salvar_incremental(
            df, FONTE, chaves=["candidato", "data"], col_tempo="data", dir_bruto=dir_bruto
        )
        log.info("GDELT %s: %s dias baixados, %s novos", candidato, len(df), n)
        total += n
    if len(falhas) == len(config.CANDIDATOS_2_TURNO):
        raise LimiteRequisicoes(f"GDELT falhou para todos os candidatos: {falhas}")
    return total
