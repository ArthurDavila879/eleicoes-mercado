"""Testes de robustez sobre os dados do dbt (chamado pelos modelos Python de ``marts``).

Recebe DataFrames das tabelas do dbt e devolve os marts de robustez:
- ``testes``: Patell, BMP e Corrado (+ CAR e t para conferência) por evento × ativo ×
  frequência, com o ajuste de Holm na família principal;
- ``sensibilidade``: CAR e p-valor (teste principal) em janelas alternativas;
- ``placebo`` / ``resultados_placebo``: distribuição de CAR em datas sem evento e p-valor
  empírico do CAR real.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from src.estatistica import estudo_evento as ee


def _series(retornos_ref: pd.DataFrame, ativos: list[str]) -> dict[str, ee.Serie]:
    df = retornos_ref[retornos_ref["ativo"].isin(ativos)]
    return {a: ee.Serie.de_dataframe(g) for a, g in df.groupby("ativo")}


def _dias_zero(janelas: pd.DataFrame) -> pd.DataFrame:
    """idx do dia/barra 0 de cada evento × ativo (idx − rel em qualquer linha)."""
    z = janelas.assign(idx0=janelas["idx"] - janelas["rel"])
    return z.groupby(["evento_id", "ativo"], as_index=False)["idx0"].first()


def _idx_em_janela(janelas: pd.DataFrame) -> dict[tuple[int, str], np.ndarray]:
    """idx das observações dentro da janela principal de cada evento × ativo."""
    ev = janelas[janelas["fase"] == "evento"]
    return {(e, a): g["idx"].to_numpy() for (e, a), g in ev.groupby(["evento_id", "ativo"])}


def _outras_janelas(em_janela: dict, evento_id: int, ativo: str) -> np.ndarray:
    partes = [v for (e, a), v in em_janela.items() if a == ativo and e != evento_id]
    return np.concatenate(partes) if partes else np.array([], dtype=np.int64)


def _todas_janelas(em_janela: dict, ativo: str) -> np.ndarray:
    partes = [v for (_, a), v in em_janela.items() if a == ativo]
    return np.concatenate(partes) if partes else np.array([], dtype=np.int64)


def testes_adicionais(
    car_eventos: pd.DataFrame,
    dados: dict[str, tuple[pd.DataFrame, pd.DataFrame]],
    parametros: dict[str, dict],
    familia_principal: list[str],
) -> pd.DataFrame:
    """Patell, BMP e Corrado na janela principal de cada evento × ativo × frequência.

    ``dados[frequencia] = (retornos_ref, janelas)``; ``parametros[frequencia]`` traz
    ``jan``, ``est`` e ``min_est``.
    """
    linhas = []
    for freq, (retornos_ref, janelas) in dados.items():
        cfg = parametros[freq]
        base = car_eventos[car_eventos["frequencia"] == freq]
        series = _series(retornos_ref, base["ativo"].unique().tolist())
        zeros = _dias_zero(janelas).set_index(["evento_id", "ativo"])["idx0"]
        em_janela = _idx_em_janela(janelas)
        for _, b in base.iterrows():
            chave = (b["evento_id"], b["ativo"])
            linha = dict(frequencia=freq, evento_id=b["evento_id"], ativo=b["ativo"])
            if chave in zeros.index and b["ativo"] in series:
                r = ee.estudo(series[b["ativo"]], int(zeros[chave]), cfg["jan"], cfg["est"],
                              _outras_janelas(em_janela, *chave), cfg["min_est"])
                if r is not None:
                    linha.update(r)
            linhas.append(linha)
    df = pd.DataFrame(linhas)
    for col in ["car", "estatistica_t", "p_valor", "z_patell", "p_patell", "t_bmp", "p_bmp",
                "z_corrado", "p_corrado", "n_obs"]:
        if col not in df:
            df[col] = np.nan

    # Holm na família principal (janela diária dos ativos de fontes distintas), por evento
    df["familia_principal"] = (df["frequencia"] == "diaria") & df["ativo"].isin(familia_principal)
    df["p_valor_holm"] = np.nan
    for _, g in df[df["familia_principal"]].groupby("evento_id"):
        df.loc[g.index, "p_valor_holm"] = ee.holm(g["p_valor"].to_numpy())
    df["n_familia_holm"] = df.groupby(["evento_id", "familia_principal"])["p_valor"].transform(
        lambda s: s.notna().sum()).where(df["familia_principal"])
    colunas = [
        "frequencia", "evento_id", "ativo", "status", "n_obs", "n_estimacao", "car",
        "estatistica_t", "p_valor", "z_patell", "p_patell", "t_bmp", "p_bmp", "z_corrado",
        "p_corrado", "familia_principal", "p_valor_holm", "n_familia_holm",
    ]
    return df.reindex(columns=colunas)


def sensibilidade(
    car_eventos: pd.DataFrame,
    retornos_ref: pd.DataFrame,
    janelas: pd.DataFrame,
    janelas_alternativas: list[tuple[int, int]],
    est: tuple[int, int],
    min_est: int,
    janela_principal: tuple[int, int],
) -> pd.DataFrame:
    """CAR e p-valor (teste t principal) em janelas alternativas (só diária).

    A estimação e a exclusão das janelas de outros eventos são as da análise principal.
    """
    base = car_eventos[car_eventos["frequencia"] == "diaria"]
    series = _series(retornos_ref, base["ativo"].unique().tolist())
    zeros = _dias_zero(janelas).set_index(["evento_id", "ativo"])["idx0"]
    em_janela = _idx_em_janela(janelas)
    linhas = []
    for _, b in base.iterrows():
        chave = (b["evento_id"], b["ativo"])
        for jan in janelas_alternativas:
            linha = dict(evento_id=b["evento_id"], ativo=b["ativo"],
                         janela=f"[{jan[0]:+d},{jan[1]:+d}]".replace("+0", "0"),
                         janela_inicio=jan[0], janela_fim=jan[1],
                         principal=tuple(jan) == tuple(janela_principal))
            if chave in zeros.index and b["ativo"] in series:
                r = ee.estudo(series[b["ativo"]], int(zeros[chave]), jan, est,
                              _outras_janelas(em_janela, *chave), min_est)
                if r is not None:
                    linha.update({k: r[k] for k in ["status", "n_obs", "n_esperado", "car",
                                                    "erro_padrao_car", "estatistica_t", "p_valor"]})
            linhas.append(linha)
    df = pd.DataFrame(linhas)
    colunas = ["evento_id", "ativo", "janela", "janela_inicio", "janela_fim", "principal",
               "status", "n_obs", "n_esperado", "car", "erro_padrao_car", "estatistica_t",
               "p_valor"]
    return df.reindex(columns=colunas)


def placebo(
    car_eventos: pd.DataFrame,
    dados: dict[str, tuple[pd.DataFrame, pd.DataFrame]],
    parametros: dict[str, dict],
    n: int,
    semente: int,
) -> pd.DataFrame:
    """Distribuição placebo de CAR por ativo × frequência × versão.

    Versões: ``restrita`` (pseudodia 0 só em início de sessão, como o evento real de
    domingo — a principal) e ``irrestrita`` (qualquer pregão/barra).
    """
    distribuicoes = []
    for freq, (retornos_ref, janelas) in dados.items():
        cfg = parametros[freq]
        base = car_eventos[car_eventos["frequencia"] == freq]
        series = _series(retornos_ref, base["ativo"].unique().tolist())
        em_janela = _idx_em_janela(janelas)
        for ativo, serie in sorted(series.items()):
            reais = _todas_janelas(em_janela, ativo)
            for versao, restrito in [("restrita", True), ("irrestrita", False)]:
                rng = ee.semente_grupo(semente, ativo, freq, versao)
                d = ee.placebo(serie, freq, cfg["jan"], cfg["est"], reais, cfg["min_est"],
                               n, rng, restrito)
                distribuicoes.append(d.assign(frequencia=freq, ativo=ativo, versao=versao))
    colunas = ["frequencia", "ativo", "versao", "idx0", "tempo0", "car", "estatistica_t"]
    if not distribuicoes:
        return pd.DataFrame(columns=colunas)
    return pd.concat(distribuicoes, ignore_index=True).reindex(columns=colunas)


def resultados_placebo(resultados: pd.DataFrame, distribuicao: pd.DataFrame) -> pd.DataFrame:
    """p-valor empírico do CAR real (só onde o teste principal tem p-valor) contra a
    distribuição placebo do mesmo ativo × frequência × versão."""
    linhas = []
    for (freq, ativo, versao), d in distribuicao.groupby(["frequencia", "ativo", "versao"]):
        cars = d["car"].to_numpy(dtype=float)
        base = resultados[(resultados["frequencia"] == freq) & (resultados["ativo"] == ativo)]
        for _, b in base.iterrows():
            ok = pd.notna(b["p_valor"])
            car_real = float(b["car"]) if ok else np.nan
            linhas.append(dict(
                frequencia=freq, evento_id=b["evento_id"], ativo=ativo, versao=versao,
                car_real=car_real, n_placebo=len(cars),
                p_empirico=ee.p_empirico(car_real, cars) if ok else np.nan,
                car_placebo_p025=np.quantile(cars, 0.025) if len(cars) else np.nan,
                car_placebo_p975=np.quantile(cars, 0.975) if len(cars) else np.nan,
                dp_car_placebo=cars.std(ddof=1) if len(cars) > 1 else np.nan,
            ))
    colunas = ["frequencia", "evento_id", "ativo", "versao", "car_real", "n_placebo",
               "p_empirico", "car_placebo_p025", "car_placebo_p975", "dp_car_placebo"]
    return pd.DataFrame(linhas, columns=colunas)


# ---------------------------------------------------------------------------------------
# Apoio aos modelos Python do dbt
# ---------------------------------------------------------------------------------------

def ler_parametros(bruto) -> dict:
    """Config ``parametros_robustez`` do dbt (JSON com as vars do projeto) → dicionário com
    ``freq`` (janelas e mínimos por frequência), ``familia_principal``,
    ``janelas_sensibilidade``, ``placebo_n`` e ``placebo_semente``."""
    v = json.loads(bruto) if isinstance(bruto, str) else dict(bruto)
    freq = {
        f: dict(jan=(int(v[f"janela_{f}_inicio"]), int(v[f"janela_{f}_fim"])),
                est=(int(v[f"estimacao_{f}_inicio"]), int(v[f"estimacao_{f}_fim"])),
                min_est=int(v[f"min_obs_estimacao_{f}"]))
        for f in ("diaria", "horaria")
    }
    return dict(
        freq=freq,
        familia_principal=list(v["familia_principal"]),
        janelas_sensibilidade=ler_janelas_sensibilidade(v["janelas_sensibilidade"]),
        placebo_n=int(v["placebo_n"]),
        placebo_semente=int(v["placebo_semente"]),
        fuso_offset_horas=int(v.get("fuso_offset_horas", -3)),
        hora_corte_pregao=int(v.get("hora_corte_pregao", 17)),
    )


def ler_janelas_sensibilidade(texto: str) -> list[tuple[int, int]]:
    """``"0,0;0,1;-1,3"`` → ``[(0, 0), (0, 1), (-1, 3)]``."""
    return [tuple(int(x) for x in par.split(",")) for par in texto.split(";") if par.strip()]
