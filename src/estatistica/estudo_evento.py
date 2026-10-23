"""Estudo de evento em Python: o mesmo procedimento dos modelos SQL do dbt, para uma série.

Usado pelos modelos Python do dbt de robustez (Patell, BMP, Corrado, placebo e
sensibilidade de janela). Reproduz exatamente as regras das macros de
``dbt/macros/estudo_evento.sql`` — o teste ``assert_robustez_igual_principal`` confere que
o CAR e o t daqui batem com ``fct_car_eventos`` nos eventos reais:

- a série é a de ``int_retornos_*_ref`` de um ativo (``idx`` contínuo por observação);
- estimação em [est_ini, est_fim] e janela em [jan_ini, jan_fim], relativas ao ``idx0``;
- observações da estimação dentro da janela de OUTRO evento são descartadas;
- só entram retornos com referência (exceto na média constante);
- mercado / mercado_global: MQO, σ² = SQR/(n−2); media_constante: média, σ² = var amostral;
  controle_moedas: AR = R − referência, σ² = var amostral.

Fórmulas dos testes adicionais: ver ``PRE_REGISTRO.md`` (seção 5).
"""

from __future__ import annotations

import zlib
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

MODELOS_COM_REFERENCIA = ("mercado", "mercado_global", "controle_moedas")


@dataclass
class Serie:
    """Série de um ativo numa frequência, em arrays alinhados por posição."""

    idx: np.ndarray
    tempo: np.ndarray
    r: np.ndarray
    ref: np.ndarray  # NaN quando não há referência
    modelo: str

    @classmethod
    def de_dataframe(cls, df: pd.DataFrame) -> "Serie":
        df = df.sort_values("idx")
        modelo = df["modelo_retorno_normal"].iloc[0]
        ref = df["r_referencia"].astype(float).to_numpy()
        if modelo == "media_constante":
            ref = np.zeros(len(df))  # a referência não é usada
        return cls(
            idx=df["idx"].astype(np.int64).to_numpy(),
            tempo=df["tempo"].to_numpy(),
            r=df["log_retorno"].astype(float).to_numpy(),
            ref=ref,
            modelo=modelo,
        )


def _graus_liberdade(modelo: str, n: int) -> int:
    return n - 2 if modelo in ("mercado", "mercado_global") else n - 1


def estimar(r: np.ndarray, ref: np.ndarray, modelo: str) -> dict:
    """Parâmetros do retorno normal na janela de estimação (mesmas regras do SQL)."""
    n = len(r)
    if modelo in ("mercado", "mercado_global"):
        media_ref = ref.mean()
        sxx = ((ref - media_ref) ** 2).sum()
        beta = ((ref - media_ref) * (r - r.mean())).sum() / sxx if sxx > 0 else np.nan
        alfa = r.mean() - beta * media_ref
        residuo = r - (alfa + beta * ref)
        sigma2 = (residuo**2).sum() / (n - 2) if n > 2 else np.nan
        return dict(alfa=alfa, beta=beta, sigma2=sigma2, n=n, media_ref=media_ref, sxx=sxx,
                    residuo=residuo)
    if modelo == "media_constante":
        alfa, beta = r.mean(), 0.0
    else:  # controle_moedas
        alfa, beta = 0.0, 1.0
    residuo = r - (alfa + beta * ref)
    sigma2 = residuo.var(ddof=1) if n > 1 else np.nan
    return dict(alfa=alfa, beta=beta, sigma2=sigma2, n=n, media_ref=np.nan, sxx=np.nan,
                residuo=residuo)


def fator_previsao(modelo: str, ref_janela: np.ndarray, p: dict) -> np.ndarray:
    """C_t da correção de Patell para o erro de previsão do retorno normal."""
    n = p["n"]
    if modelo in ("mercado", "mercado_global"):
        return 1 + 1 / n + (ref_janela - p["media_ref"]) ** 2 / p["sxx"]
    if modelo == "media_constante":
        return np.full(len(ref_janela), 1 + 1 / n)
    return np.ones(len(ref_janela))  # controle_moedas: nenhum parâmetro de média estimado


def _p_normal(z: float) -> float:
    return float(2 * stats.norm.sf(abs(z))) if np.isfinite(z) else np.nan


def _p_t(t: float, gl: float) -> float:
    return float(2 * stats.t.sf(abs(t), gl)) if np.isfinite(t) and gl > 0 else np.nan


def estudo(
    serie: Serie,
    idx0: int,
    jan: tuple[int, int],
    est: tuple[int, int],
    excluir: np.ndarray | None = None,
    min_estimacao: int = 0,
) -> dict | None:
    """Estudo de evento completo para um dia/barra 0 (``idx0``).

    ``excluir``: idx que pertencem à janela de outro evento (fora da estimação).
    Retorna ``None`` se não houver estimação ou janela com dados.
    """
    rel = serie.idx - idx0
    tem_ref = ~np.isnan(serie.ref)
    na_est = (rel >= est[0]) & (rel <= est[1]) & tem_ref
    if excluir is not None and len(excluir):
        na_est &= ~np.isin(serie.idx, excluir)
    na_jan = (rel >= jan[0]) & (rel <= jan[1]) & tem_ref
    n_est, n_obs = int(na_est.sum()), int(na_jan.sum())
    n_esperado = jan[1] - jan[0] + 1
    if n_est < 3 or n_obs == 0:
        return None

    modelo = serie.modelo
    p = estimar(serie.r[na_est], serie.ref[na_est], modelo)
    gl = _graus_liberdade(modelo, n_est)
    ref_jan = serie.ref[na_jan]
    ar = serie.r[na_jan] - (p["alfa"] + p["beta"] * ref_jan)
    sigma = np.sqrt(p["sigma2"])
    car = ar.sum()
    erro_padrao = np.sqrt(n_obs * p["sigma2"])
    t = car / erro_padrao if erro_padrao > 0 else np.nan
    status = (
        "estimacao_insuficiente" if n_est < min_estimacao
        else "janela_parcial" if n_obs < n_esperado else "completo"
    )
    valido = status != "estimacao_insuficiente" and 2 * n_obs >= n_esperado
    res = dict(
        n_estimacao=n_est, graus_liberdade=gl, n_obs=n_obs, n_esperado=n_esperado,
        status=status, alfa=p["alfa"], beta=p["beta"], sigma=sigma, car=car,
        erro_padrao_car=erro_padrao, estatistica_t=t,
        p_valor=_p_t(t, gl) if valido else np.nan,
        inicio_janela=serie.tempo[na_jan].min(), fim_janela=serie.tempo[na_jan].max(),
    )

    # --- Patell: AR padronizado com correção do erro de previsão ---
    sar = ar / (sigma * np.sqrt(fator_previsao(modelo, ref_jan, p)))
    k = n_est - gl
    if n_est - k - 2 > 0:
        z_patell = sar.sum() / np.sqrt(n_obs * (n_est - k) / (n_est - k - 2))
    else:
        z_patell = np.nan
    res["z_patell"] = z_patell
    res["p_patell"] = _p_normal(z_patell) if valido else np.nan

    # --- BMP (adaptação em série temporal: dispersão dos SAR dentro da janela) ---
    if n_obs >= 3:
        dp = sar.std(ddof=1)
        t_bmp = (sar.sum() / np.sqrt(n_obs)) / dp if dp > 0 else np.nan
        res["t_bmp"] = t_bmp
        res["p_bmp"] = _p_t(t_bmp, n_obs - 1) if valido else np.nan
    else:
        res["t_bmp"] = res["p_bmp"] = np.nan

    # --- Corrado: postos dos AR na amostra estimação + janela ---
    todos = np.concatenate([p["residuo"], ar])
    postos = stats.rankdata(todos)
    n_total = len(todos)
    desvio = postos - (n_total + 1) / 2
    s_k = np.sqrt((desvio**2).mean())
    z_corrado = desvio[-n_obs:].sum() / (np.sqrt(n_obs) * s_k) if s_k > 0 else np.nan
    res["z_corrado"] = z_corrado
    res["p_corrado"] = _p_normal(z_corrado) if valido else np.nan
    return res


# ---------------------------------------------------------------------------------------
# Placebo
# ---------------------------------------------------------------------------------------

def inicio_de_sessao(tempo: np.ndarray, frequencia: str) -> np.ndarray:
    """Marca as observações equivalentes ao dia/barra 0 de um evento de domingo:
    diário, 1º pregão após um dia sem pregão; horário, 1ª barra de um pregão (≥ 12h
    desde a barra anterior). A 1ª observação da série nunca é marcada."""
    t = pd.to_datetime(pd.Series(tempo))
    intervalo = t.diff()
    limite = pd.Timedelta(days=1) if frequencia == "diaria" else pd.Timedelta(hours=12)
    marca = intervalo > limite if frequencia == "diaria" else intervalo >= limite
    return marca.fillna(False).to_numpy()


def semente_grupo(semente: int, *chaves: str) -> np.random.Generator:
    """Gerador determinístico por grupo (ativo, frequência, versão)."""
    return np.random.default_rng([semente, zlib.crc32("|".join(chaves).encode())])


def placebo(
    serie: Serie,
    frequencia: str,
    jan: tuple[int, int],
    est: tuple[int, int],
    janelas_reais: np.ndarray,
    min_estimacao: int,
    n: int,
    rng: np.random.Generator,
    restrito: bool,
) -> pd.DataFrame:
    """CAR de pseudoeventos sorteados sem reposição entre as posições elegíveis.

    Elegível: a janela do pseudoevento cabe nos dados e não toca nenhuma janela real
    (``janelas_reais`` = idx dentro delas), há dados e estimação suficientes para o p-valor (mesmas regras do
    estudo real) e, se ``restrito``, a posição é um início de sessão.
    """
    candidatos = []
    marca = inicio_de_sessao(serie.tempo, frequencia) if restrito else np.ones(len(serie.idx), bool)
    reais = set(janelas_reais.tolist())
    ultimo = serie.idx.max()
    for pos in np.flatnonzero(marca):
        idx0 = serie.idx[pos]
        if idx0 + jan[1] > ultimo:  # janela além do fim dos dados
            continue
        if any(i in reais for i in range(idx0 + jan[0], idx0 + jan[1] + 1)):
            continue
        candidatos.append(idx0)
    candidatos = np.array(candidatos, dtype=np.int64)
    rng.shuffle(candidatos)  # ordem aleatória; percorre até juntar n válidos

    linhas = []
    for idx0 in candidatos:
        r = estudo(serie, int(idx0), jan, est, janelas_reais, min_estimacao)
        if r is None or not np.isfinite(r["p_valor"]):
            continue
        pos0 = int(np.searchsorted(serie.idx, idx0))
        linhas.append(dict(idx0=int(idx0), tempo0=serie.tempo[pos0], car=r["car"],
                           estatistica_t=r["estatistica_t"]))
        if len(linhas) >= n:
            break
    return pd.DataFrame(linhas, columns=["idx0", "tempo0", "car", "estatistica_t"])


def p_empirico(car_real: float, cars_placebo: np.ndarray) -> float:
    """p-valor empírico bicaudal: (1 + #{|CAR_placebo| ≥ |CAR_real|}) / (1 + n)."""
    if not np.isfinite(car_real) or len(cars_placebo) == 0:
        return np.nan
    return (1 + int((np.abs(cars_placebo) >= abs(car_real)).sum())) / (1 + len(cars_placebo))


def holm(p: np.ndarray) -> np.ndarray:
    """Ajuste de Holm-Bonferroni (ignora NaN; m = nº de p-valores disponíveis)."""
    p = np.asarray(p, dtype=float)
    ajustado = np.full(len(p), np.nan)
    ok = np.flatnonzero(np.isfinite(p))
    m = len(ok)
    if m == 0:
        return ajustado
    ordem = ok[np.argsort(p[ok])]
    acumulado = 0.0
    for i, j in enumerate(ordem):
        acumulado = max(acumulado, min(1.0, (m - i) * p[j]))
        ajustado[j] = acumulado
    return ajustado
