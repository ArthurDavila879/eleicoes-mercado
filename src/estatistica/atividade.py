"""Volatilidade realizada e volume anormais em torno dos eventos (análise diária).

Cada medida vira uma série diária por ativo, ``x_t`` em log:

- volatilidade realizada: ``x_t = ln Σ r_h²`` das barras de 1h do dia (data de
  America/Sao_Paulo); a barra de abertura carrega o intervalo desde o fechamento anterior.
  Dias com menos da metade das barras típicas do ativo são descartados (pregão incompleto);
- volume: ``x_t = ln(1 + V_t)`` do volume diário do Yahoo (só ativos com volume).

O nível anormal é ``x_t − média(x)`` na janela de estimação, padronizado pelo desvio-padrão
da estimação — exatamente o estudo de evento com média constante de ``estudo_evento`` (mesmas
janelas, mesmo dia 0, mesma exclusão das janelas de outros eventos). O acumulado na janela
[-1,+3] é testado com ``t = Σ(x − média) / (dp·√L)`` (t de Student, bicaudal).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.estatistica import estudo_evento as ee

COLUNAS = [
    "medida", "evento_id", "ativo", "status", "n_obs", "n_esperado", "n_estimacao",
    "inicio_janela", "fim_janela", "anormal_acumulado", "variacao_media_pct", "anormal_dia0_pct",
    "estatistica_t", "p_valor",
]


def serie_volatilidade(retornos_horarios: pd.DataFrame, fuso_offset_horas: int) -> pd.DataFrame:
    """(ativo, data, x) com x = ln da variância realizada diária das barras de 1h."""
    df = retornos_horarios.dropna(subset=["log_retorno"]).copy()
    df["data"] = (pd.to_datetime(df["tempo"]) + pd.Timedelta(hours=fuso_offset_horas)).dt.normalize()
    dia = df.groupby(["ativo", "data"]).agg(
        rv=("log_retorno", lambda r: float((r**2).sum())), n_barras=("log_retorno", "size")
    ).reset_index()
    tipico = dia.groupby("ativo")["n_barras"].transform("median")
    dia = dia[(dia["n_barras"] * 2 >= tipico) & (dia["rv"] > 0)]
    return dia.assign(x=np.log(dia["rv"]))[["ativo", "data", "x"]]


def serie_volume(volumes: pd.DataFrame) -> pd.DataFrame:
    """(ativo, data, x) com x = ln(1 + volume); só dias com volume positivo."""
    df = volumes[volumes["volume"] > 0]
    return df.assign(data=pd.to_datetime(df["data"]), x=np.log1p(df["volume"]))[["ativo", "data", "x"]]


def inicio_evento(data_local, hora_local: int, hora_corte: int) -> pd.Timestamp:
    """Primeira data que conta como dia 0 (mesma regra de int_janelas_diarias)."""
    data = pd.Timestamp(data_local).normalize()
    return data + pd.Timedelta(days=1) if hora_local >= hora_corte else data


def estudar(
    series: pd.DataFrame,
    medida: str,
    eventos: pd.DataFrame,
    jan: tuple[int, int],
    est: tuple[int, int],
    min_est: int,
    hora_corte: int,
) -> pd.DataFrame:
    """Estudo de evento do nível anormal de ``x`` para cada evento × ativo."""
    linhas = []
    for ativo, g in series.groupby("ativo"):
        g = g.sort_values("data").reset_index(drop=True)
        datas = g["data"].to_numpy()
        serie = ee.Serie(idx=np.arange(1, len(g) + 1), tempo=datas, r=g["x"].to_numpy(float),
                         ref=np.zeros(len(g)), modelo="media_constante")
        # dia 0 (idx) de cada evento: 1ª observação a partir do início do evento
        zeros = {}
        for ev in eventos.itertuples():
            pos = np.searchsorted(datas, np.datetime64(inicio_evento(ev.data_local, ev.hora_local, hora_corte)))
            if pos < len(datas):
                zeros[ev.evento_id] = int(serie.idx[pos])
        for ev in eventos.itertuples():
            linha = dict(medida=medida, evento_id=ev.evento_id, ativo=ativo)
            if ev.evento_id in zeros:
                idx0 = zeros[ev.evento_id]
                outras = np.concatenate([np.arange(z + jan[0], z + jan[1] + 1)
                                         for e, z in zeros.items() if e != ev.evento_id] or [np.array([], int)])
                r = ee.estudo(serie, idx0, jan, est, outras, min_est)
                if r is not None:
                    dia0 = ee.estudo(serie, idx0, (0, 0), est, outras, min_est)
                    linha.update(
                        status=r["status"], n_obs=r["n_obs"], n_esperado=r["n_esperado"],
                        n_estimacao=r["n_estimacao"], inicio_janela=r["inicio_janela"],
                        fim_janela=r["fim_janela"], anormal_acumulado=r["car"],
                        variacao_media_pct=(np.exp(r["car"] / r["n_obs"]) - 1) * 100,
                        anormal_dia0_pct=(np.exp(dia0["car"]) - 1) * 100 if dia0 else np.nan,
                        estatistica_t=r["estatistica_t"], p_valor=r["p_valor"],
                    )
            linha.setdefault("status", "aguardando_dados")
            linhas.append(linha)
    return pd.DataFrame(linhas).reindex(columns=COLUNAS)
