"""Volatilidade realizada (barras de 1h) e volume anormais na janela diária dos eventos.

Nível anormal em log contra a média da janela de estimação, com o mesmo dia 0, as mesmas
janelas e a mesma exclusão de outros eventos do estudo principal (src/estatistica/atividade.py).
"""

import pandas as pd

from src.estatistica import atividade, robustez


def model(dbt, session):
    dbt.config(materialized="table")
    p = robustez.ler_parametros(dbt.config.get("parametros_robustez"))
    cfg = p["freq"]["diaria"]
    eventos = dbt.ref("stg_eventos").df()
    resultados = dbt.ref("resultados_eventos").df()
    horarios = resultados.loc[resultados["frequencia"] == "horaria", "ativo"].unique()
    diarios = resultados.loc[resultados["frequencia"] == "diaria", "ativo"].unique()

    retornos_h = dbt.ref("int_retornos_horarios").df()
    vol = atividade.serie_volatilidade(retornos_h[retornos_h["ativo"].isin(horarios)], p["fuso_offset_horas"])
    volumes = dbt.ref("stg_volumes_diarios").df()
    volume = atividade.serie_volume(volumes[volumes["ativo"].isin(diarios)])

    partes = [
        atividade.estudar(vol, "volatilidade_realizada", eventos, cfg["jan"], cfg["est"], cfg["min_est"],
                          p["hora_corte_pregao"]),
        atividade.estudar(volume, "volume", eventos, cfg["jan"], cfg["est"], cfg["min_est"],
                          p["hora_corte_pregao"]),
    ]
    return pd.concat(partes, ignore_index=True)
