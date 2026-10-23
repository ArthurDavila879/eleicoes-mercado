"""Análise agregada entre eventos: CAAR e testes conjuntos (só frequência diária).

Para cada ativo e grupo de eventos (todos, 1º turnos, 2º turnos), com os CAR de cada
evento (``car_i``), seus erros-padrão da estimação (``ep_i``) e estatísticas t (``t_i``):

- **CAAR** = média dos ``car_i``;
- **t agregado** = ``Σ car_i / √(Σ ep_i²)``, normal padrão — supõe eventos independentes
  (janelas de anos diferentes) e usa as variâncias estimadas antes de cada evento;
- **t transversal** = ``CAAR / (dp(car) / √N)``, t de Student com N − 1 gl (só com N ≥ 3):
  usa a dispersão observada entre os eventos, robusta a variância maior nos eventos;
- **qui-quadrado sem direção** = ``Σ t_i²``, χ² com N gl: testa se há movimento anormal
  em qualquer direção. Eleições diferentes podem mover o preço em sentidos opostos, e a
  média com sinal (CAAR) se cancelaria; este teste não depende do sinal — é o teste neutro
  da pergunta "eleições produzem reações anormais?".
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
from scipy import stats

RE_TURNO = re.compile(r"([12])º turno")
COLUNAS = [
    "grupo", "ativo", "n_eventos", "eventos", "caar", "caar_pct", "t_agregado", "p_agregado",
    "t_transversal", "p_transversal", "qui2_sem_direcao", "p_qui2", "n_positivos",
]


def turno(descricao: str) -> str | None:
    m = RE_TURNO.search(str(descricao))
    return f"{m.group(1)}º turno" if m else None


def estatisticas(car: np.ndarray, ep: np.ndarray, t: np.ndarray) -> dict:
    """Estatísticas agregadas de N eventos (arrays alinhados, sem NaN)."""
    n = len(car)
    res = dict(n_eventos=n, caar=np.nan, t_agregado=np.nan, p_agregado=np.nan,
               t_transversal=np.nan, p_transversal=np.nan, qui2_sem_direcao=np.nan,
               p_qui2=np.nan, n_positivos=int((car > 0).sum()))
    if n == 0:
        return res
    res["caar"] = car.mean()
    if (ep > 0).all():
        res["t_agregado"] = car.sum() / np.sqrt((ep**2).sum())
        res["p_agregado"] = float(2 * stats.norm.sf(abs(res["t_agregado"])))
    if n >= 3 and car.std(ddof=1) > 0:
        res["t_transversal"] = car.mean() / (car.std(ddof=1) / np.sqrt(n))
        res["p_transversal"] = float(2 * stats.t.sf(abs(res["t_transversal"]), n - 1))
    res["qui2_sem_direcao"] = float((t**2).sum())
    res["p_qui2"] = float(stats.chi2.sf(res["qui2_sem_direcao"], n))
    return res


def caar(resultados: pd.DataFrame) -> pd.DataFrame:
    """CAAR por grupo × ativo a partir de ``resultados_eventos`` (linhas diárias com p-valor)."""
    base = resultados[(resultados["frequencia"] == "diaria") & resultados["p_valor"].notna()]
    base = base.assign(turno=base["descricao"].map(turno),
                       ano=pd.to_datetime(base["data_hora_local"]).dt.year)
    grupos = {"todos": base, "1º turno": base[base["turno"] == "1º turno"],
              "2º turno": base[base["turno"] == "2º turno"]}
    linhas = []
    for grupo, dados in grupos.items():
        for ativo, g in dados.groupby("ativo"):
            g = g.sort_values("data_hora_local")
            r = estatisticas(g["car"].to_numpy(float), g["erro_padrao_car"].to_numpy(float),
                             g["estatistica_t"].to_numpy(float))
            rotulos = ", ".join(f"{a} {t or ''}".strip() for a, t in zip(g["ano"], g["turno"]))
            linhas.append(dict(grupo=grupo, ativo=ativo, eventos=rotulos,
                               caar_pct=(np.exp(r["caar"]) - 1) * 100 if r["n_eventos"] else np.nan, **r))
    return pd.DataFrame(linhas, columns=COLUNAS)
