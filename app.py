"""Dashboard Streamlit: reação do mercado brasileiro a eventos das eleições de 2026.

Rodar: ``streamlit run app.py`` (porta 8501). Lê o DuckDB gerado por ``python -m src.pipeline``.
"""

from __future__ import annotations

from datetime import timedelta

import duckdb
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import config

st.set_page_config(page_title="Eleições 2026 × Mercado", page_icon="📈", layout="wide")

AVISO = (
    "**Aviso:** este painel é um estudo acadêmico/estatístico sobre a reação de preços de "
    "mercado a eventos eleitorais. **Não é recomendação de investimento** nem avaliação de "
    "candidatos. Correlação temporal não implica causalidade."
)

# Paleta categórica de ordem fixa (validada para daltonismo); a cor segue a entidade.
PALETA = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
CINZA = "#9a9890"
COR_ATIVO = {
    "^BVSP": PALETA[0], "PETR4.SA": PALETA[1], "VALE3.SA": PALETA[2], "ITUB4.SA": PALETA[3],
    "BBAS3.SA": PALETA[4], "BRL=X": PALETA[5], "BCB_DOLAR": PALETA[6],
}
# Candidatos: cores sem associação partidária (laranja e água), atribuídas em ordem alfabética
COR_CANDIDATO = {c: cor for c, cor in zip(sorted(config.CANDIDATOS_2_TURNO), [PALETA[1], PALETA[2]])}
NOMES_STATUS = {
    "completo": "completo",
    "janela_parcial": "janela parcial",
    "aguardando_dados": "aguardando dados",
    "estimacao_insuficiente": "estimação insuficiente",
}


@st.cache_data(ttl=600, show_spinner=False)
def consultar(sql: str) -> pd.DataFrame:
    con = duckdb.connect(str(config.CAMINHO_DUCKDB), read_only=True)
    try:
        return con.execute(sql).df()
    finally:
        con.close()


def banco_pronto() -> bool:
    if not config.CAMINHO_DUCKDB.exists():
        return False
    try:
        consultar("select 1 from marts.resultados_eventos limit 1")
        return True
    except duckdb.Error:
        return False


def marcar_eventos(fig: go.Figure, eventos: pd.DataFrame, selecionado: int | None = None) -> None:
    """Linhas verticais nos instantes dos eventos (o selecionado em destaque)."""
    for _, ev in eventos.iterrows():
        destaque = ev["evento_id"] == selecionado
        fig.add_vline(
            x=ev["data_hora_local"], line_width=2 if destaque else 1,
            line_dash="solid" if destaque else "dot", line_color="#52514e" if destaque else CINZA,
        )
        fig.add_annotation(
            x=ev["data_hora_local"], y=1, yref="paper", yanchor="bottom", showarrow=False,
            text=f"#{ev['evento_id']}", font=dict(size=11, color="#52514e"),
        )


def estilo(fig: go.Figure, titulo_y: str, altura: int = 420) -> go.Figure:
    fig.update_layout(
        height=altura, margin=dict(l=10, r=10, t=30, b=10), hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0), yaxis_title=titulo_y,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.15)", zeroline=False)
    return fig


st.title("Eleições 2026 × mercado brasileiro")
st.caption("Estudo de evento: retornos anormais de ativos brasileiros em torno de eventos eleitorais. "
           "Mesma metodologia para todos os eventos e candidatos.")
st.warning(AVISO)

if not banco_pronto():
    st.error("Banco de dados não encontrado ou incompleto. Rode `python -m src.pipeline` "
             "(ou `docker compose --profile pipeline run --rm pipeline`) e recarregue a página.")
    st.stop()

eventos = consultar("select * from staging.stg_eventos order by data_hora_utc")
ativos = consultar("select * from referencia.ativos")
nome_ativo = dict(zip(ativos["ativo"], ativos["nome"]))

# ---------------- Filtros ----------------
with st.sidebar:
    st.header("Filtros")
    rotulos_evento = {
        int(r.evento_id): f"#{r.evento_id} · {r.data_hora_local:%d/%m/%Y %H:%M} · {r.descricao[:60]}"
        for r in eventos.itertuples()
    }
    evento_id = st.selectbox("Evento", list(rotulos_evento), format_func=rotulos_evento.get) if rotulos_evento else None
    opcoes_ativos = [a for a in ativos["ativo"] if a in COR_ATIVO]
    ativos_sel = st.multiselect(
        "Ativos", opcoes_ativos, default=["^BVSP", "PETR4.SA", "BRL=X"],
        format_func=lambda a: f"{nome_ativo.get(a, a)} ({a})",
    )
    frequencia = st.radio("Frequência da análise", ["diaria", "horaria"],
                          format_func={"diaria": "Diária [-1,+3] pregões", "horaria": "Horária [-2h,+6h]"}.get)
    st.divider()
    st.caption("Horários em America/Sao_Paulo (UTC−3). Fontes: BCB/SGS, Yahoo Finance, GDELT.")

evento = eventos.set_index("evento_id").loc[evento_id] if evento_id is not None else None
if evento is not None:
    st.info(f"**Evento #{evento_id}** ({evento['tipo']}) — {evento['data_hora_local']:%d/%m/%Y %H:%M} — "
            f"{evento['descricao']}  \nFonte: {evento['fonte_url']}")

aba_tempo, aba_car, aba_real, aba_noticias, aba_metodo = st.tabs(
    ["Ativos no tempo", "CAR por evento", "Real vs. moedas de controle", "Notícias (GDELT)", "Metodologia"]
)

# ---------------- Ativos ao longo do tempo ----------------
with aba_tempo:
    if not ativos_sel:
        st.info("Selecione ao menos um ativo na barra lateral.")
    else:
        lista = ", ".join(f"'{a}'" for a in ativos_sel)
        granularidade = st.radio("Granularidade", ["Diária (todo o período)", "Horária (±10 dias do evento)"],
                                 horizontal=True)
        if granularidade.startswith("Diária"):
            precos = consultar(f"select ativo, cast(data as timestamp) as tempo, preco "
                               f"from staging.stg_precos_diarios where ativo in ({lista}) order by data")
        else:
            centro = evento["data_hora_utc"] if evento is not None else pd.Timestamp.now()
            ini, fim = centro - timedelta(days=10), centro + timedelta(days=10)
            precos = consultar(
                f"select ativo, data_hora_utc + interval (-3) hour as tempo, preco "
                f"from staging.stg_precos_horarios where ativo in ({lista}) "
                f"and data_hora_utc between '{ini}' and '{fim}' order by data_hora_utc")
        if precos.empty:
            st.info("Sem preços para os filtros escolhidos.")
        else:
            # Base 100 na primeira observação de cada ativo: escalas diferentes num eixo só
            precos["indice"] = precos.groupby("ativo")["preco"].transform(lambda s: 100 * s / s.iloc[0])
            fig = go.Figure()
            for ativo in ativos_sel:
                parte = precos[precos["ativo"] == ativo]
                fig.add_trace(go.Scatter(
                    x=parte["tempo"], y=parte["indice"], mode="lines", name=nome_ativo.get(ativo, ativo),
                    line=dict(width=2, color=COR_ATIVO.get(ativo, CINZA)),
                    customdata=parte["preco"], hovertemplate="%{y:.1f} (preço %{customdata:.4f})",
                ))
            marcar_eventos(fig, eventos, evento_id)
            st.plotly_chart(estilo(fig, "Índice (base 100)"), width="stretch")
            st.caption("Séries em base 100 na primeira observação do período. Linhas verticais = eventos "
                       "(#id); a linha cheia é o evento selecionado. Para moedas (USD/BRL), alta = real mais fraco.")

# ---------------- CAR por evento ----------------
with aba_car:
    resultados = consultar("select * from marts.resultados_eventos")
    filtro = resultados[resultados["frequencia"] == frequencia]
    if evento_id is not None:
        filtro = filtro[filtro["evento_id"] == evento_id]
    if ativos_sel:
        filtro = filtro[filtro["ativo"].isin(ativos_sel + (["BCB_DOLAR"] if "BRL=X" in ativos_sel else []))]

    tabela = pd.DataFrame({
        "Evento": filtro["evento_id"].map(lambda i: f"#{i}"),
        "Ativo": filtro["nome"],
        "Modelo": filtro["modelo_retorno_normal"].map(
            {"mercado": "modelo de mercado (Ibovespa)", "media_constante": "média constante",
             "controle_moedas": "BRL − média controles"}),
        "Janela": filtro["janela"],
        "CAR (%)": filtro["car_pct"].round(2),
        "Erro-padrão (p.p.)": (filtro["erro_padrao_car"] * 100).round(2),
        "t": filtro["estatistica_t"].round(2),
        "p-valor": filtro["p_valor"].map(
            lambda p: "—" if pd.isna(p) else "<0,0001" if p < 0.0001 else f"{p:.4f}".replace(".", ",")),
        "Signif.": filtro["significancia"].fillna("—"),
        "Obs./esperadas": filtro["n_obs"].astype(str) + "/" + filtro["n_esperado"].astype(str),
        "Status": filtro["status"].map(NOMES_STATUS),
    })
    st.dataframe(tabela, width="stretch", hide_index=True)
    st.caption("CAR = soma dos retornos anormais (log) na janela, exibido em variação %. "
               "Significância (t de Student, bicaudal): *** p<0,01 · ** p<0,05 · * p<0,10 · n.s. não significativo. "
               "'Aguardando dados' = a janela do evento ainda não aconteceu ou não foi coletada.")

    completos = filtro[filtro["status"].isin(["completo", "janela_parcial"])]
    if evento_id is not None and not completos.empty:
        ar = consultar(
            f"select ativo, rel, tempo, retorno_anormal, car_acumulado from marts.fct_retornos_anormais "
            f"where frequencia = '{frequencia}' and evento_id = {int(evento_id)} order by rel")
        ar = ar[ar["ativo"].isin(completos["ativo"])]
        fig = go.Figure()
        for ativo, parte in ar.groupby("ativo"):
            fig.add_trace(go.Scatter(
                x=parte["rel"], y=parte["car_acumulado"] * 100, mode="lines+markers",
                name=nome_ativo.get(ativo, ativo), line=dict(width=2, color=COR_ATIVO.get(ativo, CINZA)),
                marker=dict(size=8), hovertemplate="%{y:.2f}%",
            ))
        fig.add_vline(x=-0.5, line_dash="dot", line_color=CINZA)
        fig.add_hline(y=0, line_color=CINZA, line_width=1)
        unidade = "pregões" if frequencia == "diaria" else "barras de 1h"
        estilo(fig, "CAR acumulado (%)", 380).update_xaxes(title=f"Posição relativa ao evento ({unidade})", dtick=1)
        st.subheader("CAR acumulado na janela do evento")
        st.plotly_chart(fig, width="stretch")

# ---------------- Real vs. moedas de controle ----------------
with aba_real:
    moedas = consultar(
        "select ativo, cast(data as timestamp) as tempo, preco from staging.stg_precos_diarios "
        "where ativo in ('BRL=X', 'MXN=X', 'CLP=X', 'COP=X', 'ZAR=X') order by data")
    if moedas.empty:
        st.info("Sem dados de moedas.")
    else:
        janela_dias = st.slider("Dias ao redor do evento selecionado (0 = período todo)", 0, 120, 30, step=5)
        if janela_dias and evento is not None:
            centro = pd.Timestamp(evento["data_local"])
            moedas = moedas[(moedas["tempo"] >= centro - timedelta(days=janela_dias))
                            & (moedas["tempo"] <= centro + timedelta(days=janela_dias))]
        larga = moedas.pivot_table(index="tempo", columns="ativo", values="preco").sort_index().ffill().dropna()
        if larga.empty:
            st.info("Sem dados suficientes no intervalo.")
        else:
            indice = 100 * larga / larga.iloc[0]
            controles = [c for c in ["MXN=X", "CLP=X", "COP=X", "ZAR=X"] if c in indice]
            indice["Média controles"] = indice[controles].mean(axis=1)
            fig = go.Figure()
            for c in controles:
                fig.add_trace(go.Scatter(x=indice.index, y=indice[c], mode="lines", name=nome_ativo.get(c, c),
                                         line=dict(width=1, color=CINZA), opacity=0.7, hovertemplate="%{y:.2f}"))
            fig.add_trace(go.Scatter(x=indice.index, y=indice["Média controles"], mode="lines",
                                     name="Média das moedas de controle",
                                     line=dict(width=2, color=PALETA[1]), hovertemplate="%{y:.2f}"))
            if "BRL=X" in indice:
                fig.add_trace(go.Scatter(x=indice.index, y=indice["BRL=X"], mode="lines", name="Real (USD/BRL)",
                                         line=dict(width=2.5, color=COR_ATIVO["BRL=X"]), hovertemplate="%{y:.2f}"))
            marcar_eventos(fig, eventos, evento_id)
            st.plotly_chart(estilo(fig, "Índice (base 100) — alta = moeda local mais fraca"), width="stretch")

            if "BRL=X" in indice:
                diferencial = 100 * (indice["BRL=X"] / indice["Média controles"] - 1)
                fig2 = go.Figure(go.Scatter(x=diferencial.index, y=diferencial, mode="lines",
                                            name="Real vs. controles", line=dict(width=2, color=COR_ATIVO["BRL=X"]),
                                            hovertemplate="%{y:.2f}%"))
                fig2.add_hline(y=0, line_color=CINZA, line_width=1)
                marcar_eventos(fig2, eventos, evento_id)
                st.subheader("Desempenho relativo do real")
                st.plotly_chart(estilo(fig2, "USD/BRL relativo aos controles (%)", 300), width="stretch")
                st.caption("Positivo = o real se desvalorizou mais que a média de MXN, CLP, COP e ZAR desde o "
                           "início do intervalo; é a intuição por trás do retorno anormal do real.")

    st.subheader("Séries do Banco Central (SGS)")
    bcb = consultar("select serie_nome, cast(data as timestamp) as data, valor from staging.stg_bcb_series order by data")
    if bcb.empty:
        st.info("Sem dados do BCB.")
    else:
        colunas = st.columns(3)
        titulos = {"dolar_venda": "Dólar venda (R$)", "euro_venda": "Euro venda (R$)", "meta_selic": "Meta Selic (% a.a.)"}
        for coluna, (serie, titulo) in zip(colunas, titulos.items()):
            parte = bcb[bcb["serie_nome"] == serie]
            fig = go.Figure(go.Scatter(x=parte["data"], y=parte["valor"], mode="lines",
                                       line=dict(width=2, color=PALETA[0]), name=titulo, hovertemplate="%{y:.4f}"))
            marcar_eventos(fig, eventos, evento_id)
            with coluna:
                st.markdown(f"**{titulo}**")
                st.plotly_chart(estilo(fig, "", 260).update_layout(showlegend=False), width="stretch")

# ---------------- Notícias (GDELT) ----------------
with aba_noticias:
    gdelt = consultar("select * from staging.stg_gdelt order by data")
    if gdelt.empty:
        st.info("Sem dados do GDELT ainda.")
    else:
        st.caption("Mesma consulta-base para cada candidato do 2º turno: "
                   + " · ".join(f"`{c}`" for c in gdelt["consulta"].unique())
                   + ". Os níveis absolutos não são comparáveis entre nomes; compare a dinâmica (volume relativo à "
                     "média do próprio candidato) e o tom. O GDELT só pesquisa ~3 meses para trás e tem dias sem "
                     "resposta (lacunas no gráfico); por isso é apenas descritivo, fora do teste estatístico.")
        metrica = st.radio("Métrica", ["Volume relativo", "Nº de artigos", "Tom médio"], horizontal=True)
        coluna = {"Volume relativo": "volume_relativo", "Nº de artigos": "n_artigos", "Tom médio": "tom_medio"}[metrica]
        fig = go.Figure()
        for candidato, parte in gdelt.groupby("candidato"):
            # Dias sem resposta do GDELT ficam como lacunas (não são interpolados)
            parte = parte.set_index(pd.to_datetime(parte["data"]))[[coluna]].asfreq("D").reset_index()
            fig.add_trace(go.Scatter(x=parte["data"], y=parte[coluna], mode="lines+markers", name=candidato,
                                     marker=dict(size=4), connectgaps=False,
                                     line=dict(width=2, color=COR_CANDIDATO.get(candidato, CINZA)),
                                     hovertemplate="%{y:.2f}"))
        marcar_eventos(fig, eventos, evento_id)
        st.plotly_chart(estilo(fig, metrica), width="stretch")

# ---------------- Metodologia ----------------
with aba_metodo:
    st.markdown("""
- **Retornos:** log-retornos fechamento a fechamento (diário) e barra a barra de 1h (horário).
- **Dia/barra 0:** primeiro pregão na data do evento (ou o seguinte, se o evento ocorre a partir das 17h
  ou fora de pregão); na análise horária, a primeira barra que começa no instante do evento ou depois.
- **Retorno normal:**
  - ações: modelo de mercado `R = α + β·R_Ibovespa`, estimado por MQO em [-120, -11] pregões
    ([-300, -11] barras na análise horária);
  - Ibovespa: média constante na mesma janela (não há índice de mercado mais amplo na amostra);
  - real (USD/BRL, Yahoo e BCB): retorno anormal = retorno do real − média de MXN, CLP, COP e ZAR.
- **CAR** = soma dos retornos anormais na janela [-1,+3] pregões ou [-2h,+6h];
  `t = CAR / (σ·√L)`, com σ estimado na janela de estimação e p-valor da t de Student.
- Observações de estimação que caem na janela de outro evento são descartadas.
- **Limitações:** poucos eventos, eventos e notícias sobrepostos, choques globais no mesmo dia,
  e correlação temporal não é causalidade.
""")

st.divider()
st.caption(AVISO)
