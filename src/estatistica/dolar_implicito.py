"""Dólar implícito no bitcoin: a reação do real enquanto o câmbio oficial está fechado.

``USD/BRL implícito = BTCBRL / BTCUSDT`` (Binance, mesmo instante, USDT ≈ USD). O bitcoin
negocia 24 h por dia, então dá para ver o real entre o fim da votação (domingo) e a abertura
de segunda, quando o câmbio e a B3 ainda estão fechados.

Preço num instante T = fechamento da barra de 1h que termina em T (começa em T − 1h). Para
cada evento:

- ``pre_evento``: sexta 17h → domingo, instante do evento (o fim de semana antes do resultado);
- ``reacao``: instante do evento → segunda 10h de Brasília (13h UTC, abertura da B3);
- ``fim_de_semana``: sexta 17h → segunda 10h (soma dos dois);
- ``oficial_fim_de_semana``: o mesmo intervalo no USD/BRL do Yahoo (``BRL=X``), para comparar.

Significância da ``reacao`` por placebo: o mesmo intervalo (mesmo dia da semana e hora do
evento → segunda 13h UTC) em todos os outros fins de semana com dados, sem os dos eventos;
p-valor empírico bicaudal ``(1 + #{|x_placebo| ≥ |x|}) / (1 + n)``.

Limitação: o BTCBRL tem pouca liquidez (mediana de ~2 BTC/h na Binance, menos ainda de
madrugada) e carrega um ágio/deságio próprio em relação ao câmbio oficial; o "dólar
implícito" é um sinal ruidoso, não uma cotação de câmbio.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.estatistica import estudo_evento as ee

COLUNAS_EVENTO = [
    "evento_id", "instante_evento_utc", "sexta_utc", "abertura_utc", "pre_evento", "reacao",
    "fim_de_semana", "oficial_fim_de_semana", "n_placebo", "dp_placebo", "z_reacao",
    "p_empirico", "volume_btc_reacao", "volume_btc_mediano_placebo", "agio_medio",
]


def valor_em(serie: pd.Series, instante) -> float:
    """Preço no instante T: fechamento da barra que termina em T (índice = início da barra)."""
    chave = pd.Timestamp(instante) - pd.Timedelta(hours=1)
    v = serie.get(chave, np.nan)
    return float(v) if pd.notna(v) else np.nan


def valor_ate(serie: pd.Series, instante, tolerancia_horas: int = 3) -> float:
    """Como ``valor_em``, mas aceita a última barra que termina até ``tolerancia_horas`` antes
    de T (o câmbio oficial tem lacunas de barras nos horários de pouco negócio)."""
    fim = pd.Timestamp(instante) - pd.Timedelta(hours=1)
    trecho = serie[(serie.index <= fim) & (serie.index >= fim - pd.Timedelta(hours=tolerancia_horas))].dropna()
    return float(trecho.iloc[-1]) if len(trecho) else np.nan


def soma_volume(volume: pd.Series, inicio, fim) -> float:
    """Volume das barras que começam em [inicio, fim)."""
    return float(volume[(volume.index >= pd.Timestamp(inicio)) & (volume.index < pd.Timestamp(fim))].sum())


def instantes(evento_utc) -> tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp]:
    """(sexta 17h de Brasília, evento, próxima segunda 10h de Brasília) em UTC."""
    ev = pd.Timestamp(evento_utc)
    dia = ev.normalize()
    sexta = dia - pd.Timedelta(days=(dia.day_of_week - 4) % 7) + pd.Timedelta(hours=20)
    dias_ate_segunda = (7 - dia.day_of_week) % 7 or 7
    abertura = dia + pd.Timedelta(days=dias_ate_segunda, hours=13)
    return sexta, ev, abertura


def _log(a: float, b: float) -> float:
    return float(np.log(b / a)) if a > 0 and b > 0 else np.nan


def placebo(implicito: pd.Series, evento_utc, excluir: list) -> pd.DataFrame:
    """Reação no mesmo intervalo (dia/hora do evento → segunda 13h UTC) em outros fins de semana."""
    _, ev, abertura = instantes(evento_utc)
    duracao = abertura - ev
    if implicito.empty:
        return pd.DataFrame(columns=["instante", "reacao"])
    inicio, fim = implicito.index.min(), implicito.index.max()
    excluir_dias = {pd.Timestamp(e).normalize() for e in excluir}
    linhas = []
    t = ev
    while t - pd.Timedelta(days=7) >= inicio:
        t -= pd.Timedelta(days=7)
    while t + duracao <= fim + pd.Timedelta(hours=1):
        if t.normalize() not in excluir_dias:
            x = _log(valor_em(implicito, t), valor_em(implicito, t + duracao))
            if np.isfinite(x):
                linhas.append(dict(instante=t, reacao=x))
        t += pd.Timedelta(days=7)
    return pd.DataFrame(linhas, columns=["instante", "reacao"])


def estudar(horario: pd.DataFrame, oficial: pd.DataFrame, eventos: pd.DataFrame):
    """Medidas por evento e distribuição placebo.

    ``horario``: data_hora_utc, dolar_implicito, volume_btc (de stg_dolar_implicito_horario);
    ``oficial``: barras de 1h do BRL=X (data_hora_utc, preco); ``eventos``: stg_eventos.
    """
    h = horario.set_index("data_hora_utc").sort_index()
    impl, volume = h["dolar_implicito"], h["volume_btc"]
    brl = oficial.set_index("data_hora_utc")["preco"].sort_index()
    todos_eventos = list(eventos["data_hora_utc"])
    linhas, dists = [], []
    for ev in eventos.itertuples():
        sexta, t_ev, abertura = instantes(ev.data_hora_utc)
        d_sexta, d_ev, d_ab = valor_em(impl, sexta), valor_em(impl, t_ev), valor_em(impl, abertura)
        if not np.isfinite(d_ev) or not np.isfinite(d_ab):
            continue  # sem bitcoin em reais nessa época, ou evento ainda por vir
        dist = placebo(impl, t_ev, todos_eventos)
        reacao = _log(d_ev, d_ab)
        x = dist["reacao"].to_numpy()
        vols = [soma_volume(volume, i, i + (abertura - t_ev)) for i in dist["instante"]]
        janela = h.loc[(h.index >= sexta) & (h.index < abertura)]
        oficial_janela = brl.reindex(janela.index)
        agio = np.log(janela["dolar_implicito"] / oficial_janela).dropna()
        linhas.append(dict(
            evento_id=ev.evento_id, instante_evento_utc=t_ev, sexta_utc=sexta, abertura_utc=abertura,
            pre_evento=_log(d_sexta, d_ev), reacao=reacao, fim_de_semana=_log(d_sexta, d_ab),
            oficial_fim_de_semana=_log(valor_ate(brl, sexta), valor_ate(brl, abertura)),
            n_placebo=len(x), dp_placebo=x.std(ddof=1) if len(x) > 1 else np.nan,
            z_reacao=reacao / x.std(ddof=1) if len(x) > 1 else np.nan,
            p_empirico=ee.p_empirico(reacao, x),
            volume_btc_reacao=soma_volume(volume, t_ev, abertura),
            volume_btc_mediano_placebo=float(np.median(vols)) if vols else np.nan,
            agio_medio=float(agio.mean()) if len(agio) else np.nan,
        ))
        dists.append(dist.assign(evento_id=ev.evento_id))
    eventos_df = pd.DataFrame(linhas, columns=COLUNAS_EVENTO)
    dist_df = (pd.concat(dists, ignore_index=True) if dists
               else pd.DataFrame(columns=["instante", "reacao", "evento_id"]))
    return eventos_df, dist_df[["evento_id", "instante", "reacao"]]
