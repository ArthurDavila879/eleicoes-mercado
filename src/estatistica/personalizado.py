"""Estudo de evento para uma data/hora escolhida no dashboard ("Evento personalizado").

Usa exatamente o procedimento do estudo principal (``estudo_evento.estudo``): mesmo modelo de
retorno normal do ativo, mesma janela de estimação e exclusão das janelas dos eventos de
``data/eventos.csv`` da estimação. O dia/barra 0 segue as mesmas regras:

- diária: 1º pregão na data local do evento; se a hora local for a partir do corte (17h,
  fechamento da B3), o pregão seguinte;
- horária: 1ª barra de 1h que começa no instante do evento ou depois.

É exploratório: testar muitas datas até achar uma "significativa" produz falsos positivos.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.estatistica import estudo_evento as ee


def idx_dia_zero(
    serie: pd.DataFrame, instante_local: pd.Timestamp, frequencia: str, hora_corte: int,
    fuso_offset_horas: int,
) -> int | None:
    """idx da 1ª observação que conta como dia/barra 0 (None se ainda não há dados)."""
    instante_local = pd.Timestamp(instante_local)
    tempo = pd.to_datetime(serie["tempo"])
    if frequencia == "diaria":
        inicio = instante_local.normalize()
        if instante_local.hour >= hora_corte:
            inicio += pd.Timedelta(days=1)
    else:
        inicio = instante_local - pd.Timedelta(hours=fuso_offset_horas)  # local → UTC
    depois = serie[tempo >= inicio]
    return int(depois["idx"].min()) if len(depois) else None


def estudar(
    retornos_ref: pd.DataFrame,
    janelas_reais: pd.DataFrame,
    ativo: str,
    instante_local,
    frequencia: str,
    jan: tuple[int, int],
    est: tuple[int, int],
    min_est: int,
    hora_corte: int = 17,
    fuso_offset_horas: int = -3,
) -> tuple[dict | None, pd.DataFrame]:
    """Resultado do estudo (dict de ``estudo_evento.estudo``) e os AR da janela, passo a passo.

    ``retornos_ref``: int_retornos_{diarios,horarios}_ref; ``janelas_reais``: int_janelas_* (só
    as linhas da fase 'evento' são usadas, para excluir da estimação as janelas dos eventos reais).
    """
    df = retornos_ref[retornos_ref["ativo"] == ativo].sort_values("idx")
    vazio = pd.DataFrame(columns=["rel", "tempo", "retorno_anormal", "car_acumulado"])
    if df.empty:
        return None, vazio
    idx0 = idx_dia_zero(df, instante_local, frequencia, hora_corte, fuso_offset_horas)
    if idx0 is None:
        return None, vazio
    serie = ee.Serie.de_dataframe(df)
    reais = janelas_reais[(janelas_reais["ativo"] == ativo) & (janelas_reais["fase"] == "evento")]
    # a janela do próprio instante escolhido não é excluída (ela não entra na estimação)
    excluir = reais.loc[~reais["idx"].between(idx0 + jan[0], idx0 + jan[1]), "idx"].to_numpy()
    res = ee.estudo(serie, idx0, jan, est, excluir, min_est)
    if res is None:
        return None, vazio
    rel = serie.idx - idx0
    na_jan = (rel >= jan[0]) & (rel <= jan[1]) & ~np.isnan(serie.ref)
    ar = serie.r[na_jan] - (res["alfa"] + res["beta"] * serie.ref[na_jan])
    passos = pd.DataFrame({"rel": rel[na_jan], "tempo": serie.tempo[na_jan], "retorno_anormal": ar})
    passos["car_acumulado"] = passos["retorno_anormal"].cumsum()
    return res, passos
