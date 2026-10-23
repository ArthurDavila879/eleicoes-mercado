"""Dashboard Streamlit: reação do mercado brasileiro a eventos das eleições de 2026.

Rodar: ``streamlit run app.py`` (porta 8501). Lê o DuckDB gerado por ``python -m src.pipeline``.
"""

from __future__ import annotations

from datetime import timedelta

import duckdb
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

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
# Formato do preço no hover, por classe de ativo (Ibovespa em pontos, ações em R$, moedas com 4 casas)
FORMATO_PRECO = {"indice": "%{customdata:,.0f} pts", "acao": "R$ %{customdata:,.2f}"}
FORMATO_PRECO_PADRAO = "%{customdata:,.4f}"
Z_95 = 1.959964


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


def rotulo_curto(ev) -> str:
    """'1º turno' a partir de '1º turno: encerramento...'; cai no #id se não houver prefixo."""
    prefixo = str(ev["descricao"]).split(":")[0].strip()
    return prefixo if len(prefixo) <= 25 else f"#{ev['evento_id']}"


def fmt_pct(valor: float, casas: int = 1) -> str:
    return f"{valor:+.{casas}f}%".replace(".", ",")


def marcar_eventos(fig: go.Figure, eventos: pd.DataFrame, selecionado: int | None = None,
                   janela: tuple | None = None, rotulos: bool = True) -> None:
    """Linhas verticais nos instantes dos eventos (o selecionado em destaque) e, se houver,
    a janela do evento selecionado sombreada."""
    if janela is not None:
        fig.add_vrect(x0=janela[0], x1=janela[1], fillcolor=CINZA, opacity=0.15, line_width=0, layer="below")
    for _, ev in eventos.iterrows():
        destaque = ev["evento_id"] == selecionado
        fig.add_vline(
            x=ev["data_hora_local"], line_width=1.5 if destaque else 1,
            line_dash="solid" if destaque else "dot", line_color=CINZA,
        )
        if not rotulos:
            continue
        fig.add_annotation(
            x=ev["data_hora_local"], y=1, yref="paper", yanchor="bottom", showarrow=False,
            text=f"<b>{rotulo_curto(ev)}</b>" if destaque else rotulo_curto(ev), font=dict(size=11),
        )


def estilo(fig: go.Figure, titulo_y: str, altura: int = 420, datas: bool = True) -> go.Figure:
    """Layout comum: fundo transparente (segue o tema claro/escuro do Streamlit), grade discreta,
    legenda horizontal no topo e separadores decimais brasileiros."""
    fig.update_layout(
        height=altura, margin=dict(l=10, r=10, t=40, b=10), hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.06, x=0, title_text=""),
        yaxis_title=titulo_y, separators=",.", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(namelength=-1),
    )
    fig.update_xaxes(showgrid=False, showline=True, linecolor="rgba(128,128,128,0.4)")
    if datas:
        fig.update_xaxes(hoverformat="%d/%m/%Y %H:%M", tickformatstops=[
            dict(dtickrange=[None, 86_400_000], value="%d/%m %Hh"),
            dict(dtickrange=[86_400_000, "M1"], value="%d/%m"),
            dict(dtickrange=["M1", None], value="%m/%Y"),
        ])
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
classe_ativo = dict(zip(ativos["ativo"], ativos["classe"]))
resultados = consultar("select * from marts.resultados_eventos")

# ---------------- Filtros ----------------
with st.sidebar:
    st.header("Filtros")
    rotulos_evento = {
        int(r.evento_id): f"{rotulo_curto(r._asdict())} · {r.data_hora_local:%d/%m/%Y %H:%M}"
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
res_evento = resultados[resultados["evento_id"] == evento_id] if evento_id is not None else resultados.iloc[0:0]


def janela_evento(freq: str) -> tuple | None:
    """Início/fim da janela do evento selecionado (pela série do Ibovespa), no horário local."""
    linha = res_evento[(res_evento["frequencia"] == freq) & (res_evento["ativo"] == "^BVSP")]
    if linha.empty or pd.isna(linha["inicio_janela"].iloc[0]):
        return None
    ini, fim = linha["inicio_janela"].iloc[0], linha["fim_janela"].iloc[0]
    if freq == "diaria":
        return ini - timedelta(hours=12), fim + timedelta(hours=12)
    # Barras horárias vêm em UTC e marcam o início da barra
    return ini - timedelta(hours=3), fim - timedelta(hours=2)


# ---------------- Cabeçalho do evento ----------------
if evento is not None:
    with st.container(border=True):
        st.markdown(f"#### {rotulo_curto({'descricao': evento['descricao'], 'evento_id': evento_id})} — "
                    f"{evento['data_hora_local']:%d/%m/%Y às %H:%M}")
        st.caption(f"{evento['descricao']} · [fonte]({evento['fonte_url']})")
        diario = res_evento[res_evento["frequencia"] == "diaria"].set_index("ativo")
        prontos = diario[diario["status"].isin(["completo", "janela_parcial"])]
        if prontos.empty:
            st.info("**Aguardando dados.** A janela [-1,+3] pregões deste evento ainda não aconteceu ou não foi "
                    "coletada; os resultados aparecem sozinhos depois da próxima coleta que trouxer esses pregões.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            for col, ativo, rotulo in [(c1, "^BVSP", "Ibovespa — CAR [-1,+3]"),
                                       (c2, "BRL=X", "Real vs. controles — CAR [-1,+3]")]:
                if ativo in prontos.index:
                    linha = prontos.loc[ativo]
                    col.metric(rotulo, f"{fmt_pct(linha['car_pct'])} {linha['significancia']}",
                               help=f"p-valor {linha['p_valor']:.4f}".replace(".", ","))
            significativos = int((prontos["p_valor"] < 0.05).sum())
            c3.metric("Ativos com p < 0,05", f"{significativos} de {len(prontos)}")
            c4.metric("Janela", "completa" if (prontos["status"] == "completo").all() else "parcial")

aba_car, aba_tempo, aba_real, aba_noticias, aba_metodo = st.tabs(
    ["CAR por evento", "Ativos no tempo", "Real vs. moedas de controle", "Notícias (GDELT)", "Metodologia"]
)

# ---------------- CAR por evento ----------------
with aba_car:
    filtro = res_evento[res_evento["frequencia"] == frequencia]
    if ativos_sel:
        filtro = filtro[filtro["ativo"].isin(ativos_sel + (["BCB_DOLAR"] if "BRL=X" in ativos_sel else []))]
    completos = filtro[filtro["status"].isin(["completo", "janela_parcial"])]

    if filtro.empty:
        st.info("Selecione um evento e ao menos um ativo na barra lateral.")
    elif completos.empty:
        st.info("**Aguardando dados** para este evento nesta frequência: não há gráfico ainda. "
                "A tabela abaixo lista os ativos que serão avaliados.")
    else:
        col_barras, col_linha = st.columns(2)
        # CAR com intervalo de 95% (calculado em log e convertido para variação %)
        dados = completos.sort_values("car_pct")
        lim_inf = (np.exp(dados["car"] - Z_95 * dados["erro_padrao_car"]) - 1) * 100
        lim_sup = (np.exp(dados["car"] + Z_95 * dados["erro_padrao_car"]) - 1) * 100
        nomes = dados["nome"].tolist()
        fig = go.Figure(go.Bar(
            x=dados["car_pct"], y=nomes, orientation="h", width=0.55,
            marker=dict(color=[COR_ATIVO.get(a, CINZA) for a in dados["ativo"]], cornerradius=4),
            error_x=dict(type="data", symmetric=False, array=lim_sup - dados["car_pct"],
                         arrayminus=dados["car_pct"] - lim_inf, color=CINZA, thickness=1.5, width=4),
            customdata=np.stack([lim_inf, lim_sup, dados["p_valor"]], axis=1),
            hovertemplate="CAR %{x:.2f}%<br>IC 95%: %{customdata[0]:.2f}% a %{customdata[1]:.2f}%"
                          "<br>p-valor %{customdata[2]:.4f}<extra>%{y}</extra>",
        ))
        # Rótulo depois da ponta da barra de erro, para não colidir com ela
        for nome, v, s_, ini_, fim_ in zip(nomes, dados["car_pct"], dados["significancia"].fillna(""), lim_inf, lim_sup):
            fig.add_annotation(x=fim_ if v >= 0 else ini_, y=nome, text=f"{fmt_pct(v)} {s_}", showarrow=False,
                               xanchor="left" if v >= 0 else "right", xshift=6 if v >= 0 else -6, font=dict(size=12))
        alcance = max(abs(lim_inf).max(), abs(lim_sup).max()) * 1.45
        fig.update_xaxes(range=[-alcance if lim_inf.min() < 0 else -alcance * 0.15, alcance])
        fig.add_vline(x=0, line_color=CINZA, line_width=1)
        altura_car = max(380, 80 + 60 * len(dados))
        estilo(fig, "", altura_car, datas=False).update_layout(
            hovermode="closest", showlegend=False, xaxis_title="CAR (%) com intervalo de 95%",
            margin=dict(l=10, r=60, t=10, b=10))
        fig.update_xaxes(showgrid=True, gridcolor="rgba(128,128,128,0.15)")
        with col_barras:
            st.markdown("**CAR na janela do evento**")
            st.plotly_chart(fig, width="stretch")

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
        estilo(fig, "CAR acumulado (%)", altura_car, datas=False).update_xaxes(
            title=f"Posição relativa ao evento ({unidade})", dtick=1)
        with col_linha:
            st.markdown("**CAR acumulado, passo a passo**")
            st.plotly_chart(fig, width="stretch")

    if not filtro.empty:
        tabela = pd.DataFrame({
            "Ativo": filtro["nome"],
            "Modelo": filtro["modelo_retorno_normal"].map(
                {"mercado": "modelo de mercado (Ibovespa)", "media_constante": "média constante",
                 "controle_moedas": "BRL − média controles"}),
            "Janela": filtro["janela"],
            "CAR (%)": filtro["car_pct"],
            "Erro-padrão (p.p.)": filtro["erro_padrao_car"] * 100,
            "t": filtro["estatistica_t"],
            "p-valor": filtro["p_valor"].map(
                lambda p: "—" if pd.isna(p) else "<0,0001" if p < 0.0001 else f"{p:.4f}".replace(".", ",")),
            "Signif.": filtro["significancia"].fillna("—"),
            "Obs./esperadas": filtro["n_obs"].astype(str) + "/" + filtro["n_esperado"].astype(str),
            "Status": filtro["status"].map(NOMES_STATUS),
        }).sort_values("CAR (%)", ascending=False, na_position="last")
        st.dataframe(
            tabela, width="stretch", hide_index=True,
            column_config={
                "CAR (%)": st.column_config.NumberColumn(format="%.2f"),
                "Erro-padrão (p.p.)": st.column_config.NumberColumn(format="%.2f"),
                "t": st.column_config.NumberColumn(format="%.2f"),
            },
        )
    st.caption("CAR = soma dos retornos anormais (log) na janela, exibido em variação %. Barras de erro = "
               "intervalo de 95% (±1,96 erro-padrão). Significância (t de Student, bicaudal): *** p<0,01 · "
               "** p<0,05 · * p<0,10 · n.s. não significativo. Para o real, CAR negativo = real mais forte "
               "que os pares.")

# ---------------- Ativos ao longo do tempo ----------------
with aba_tempo:
    if not ativos_sel:
        st.info("Selecione ao menos um ativo na barra lateral.")
    else:
        lista = ", ".join(f"'{a}'" for a in ativos_sel)
        granularidade = st.radio("Granularidade", ["Diária (todo o período)", "Horária (±10 dias do evento)"],
                                 horizontal=True)
        if granularidade.startswith("Diária"):
            janela = janela_evento("diaria")
            precos = consultar(f"select ativo, cast(data as timestamp) as tempo, preco "
                               f"from staging.stg_precos_diarios where ativo in ({lista}) order by data")
        else:
            janela = janela_evento("horaria")
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
                formato = FORMATO_PRECO.get(classe_ativo.get(ativo), FORMATO_PRECO_PADRAO)
                fig.add_trace(go.Scatter(
                    x=parte["tempo"], y=parte["indice"], mode="lines", name=nome_ativo.get(ativo, ativo),
                    line=dict(width=2, color=COR_ATIVO.get(ativo, CINZA)),
                    customdata=parte["preco"], hovertemplate=f"%{{y:.1f}} ({formato})",
                ))
            marcar_eventos(fig, eventos, evento_id, janela)
            fig.add_hline(y=100, line_color=CINZA, line_width=1, line_dash="dot")
            st.plotly_chart(estilo(fig, "Índice (base 100)", 460), width="stretch")
            st.caption("Séries em base 100 na primeira observação do período. Linhas verticais = eventos; a faixa "
                       "sombreada é a janela do evento selecionado. Para moedas (USD/BRL), alta = real mais fraco.")

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
            tem_real = "BRL=X" in indice
            fig = make_subplots(rows=2 if tem_real else 1, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                                row_heights=[0.65, 0.35] if tem_real else [1.0])
            for c in controles:
                fig.add_trace(go.Scatter(x=indice.index, y=indice[c], mode="lines", name=nome_ativo.get(c, c),
                                         line=dict(width=1, color=CINZA), opacity=0.6, hovertemplate="%{y:.2f}",
                                         legendgroup="controles"), row=1, col=1)
            fig.add_trace(go.Scatter(x=indice.index, y=indice["Média controles"], mode="lines",
                                     name="Média das moedas de controle",
                                     line=dict(width=2, color=PALETA[1]), hovertemplate="%{y:.2f}"), row=1, col=1)
            if tem_real:
                fig.add_trace(go.Scatter(x=indice.index, y=indice["BRL=X"], mode="lines", name="Real (USD/BRL)",
                                         line=dict(width=2.5, color=COR_ATIVO["BRL=X"]), hovertemplate="%{y:.2f}"),
                              row=1, col=1)
                diferencial = 100 * (indice["BRL=X"] / indice["Média controles"] - 1)
                fig.add_trace(go.Scatter(x=diferencial.index, y=diferencial, mode="lines",
                                         name="Real relativo aos controles (%)", showlegend=False,
                                         line=dict(width=2, color=COR_ATIVO["BRL=X"]), fill="tozeroy",
                                         fillcolor="rgba(0,131,0,0.12)", hovertemplate="%{y:.2f}%"),
                              row=2, col=1)
                fig.add_hline(y=0, line_color=CINZA, line_width=1, row=2, col=1)
                fig.update_yaxes(title_text="Real vs. controles (%)", row=2, col=1)
            marcar_eventos(fig, eventos, evento_id, janela_evento("diaria"))
            estilo(fig, "Índice (base 100)", 620 if tem_real else 420)
            fig.update_yaxes(title_text="Índice (base 100)", row=1, col=1)
            st.plotly_chart(fig, width="stretch")
            st.caption("Em cima: moedas em base 100 (alta = moeda local mais fraca frente ao dólar). Embaixo: "
                       "desempenho do real relativo à média de MXN, CLP, COP e ZAR desde o início do intervalo; "
                       "positivo = real mais fraco que os pares. É a intuição por trás do retorno anormal do real.")

    st.subheader("Séries do Banco Central (SGS)")
    bcb = consultar("select serie_nome, cast(data as timestamp) as data, valor from staging.stg_bcb_series order by data")
    if bcb.empty:
        st.info("Sem dados do BCB.")
    else:
        colunas = st.columns(3)
        titulos = {"dolar_venda": ("Dólar venda", "R$ %{y:.4f}"), "euro_venda": ("Euro venda", "R$ %{y:.4f}"),
                   "meta_selic": ("Meta Selic", "%{y:.2f}% a.a.")}
        for coluna, (serie, (titulo, formato)) in zip(colunas, titulos.items()):
            parte = bcb[bcb["serie_nome"] == serie]
            fig = go.Figure(go.Scatter(x=parte["data"], y=parte["valor"], mode="lines", line_shape="hv"
                                       if serie == "meta_selic" else "linear",
                                       line=dict(width=2, color=PALETA[0]), name=titulo, hovertemplate=formato))
            marcar_eventos(fig, eventos, evento_id, rotulos=False)
            with coluna:
                ultimo = parte.iloc[-1] if not parte.empty else None
                valor = "—" if ultimo is None else (f"{ultimo['valor']:.2f}".replace(".", ",") + "% a.a."
                                                    if serie == "meta_selic"
                                                    else f"R$ {ultimo['valor']:.4f}".replace(".", ","))
                st.metric(titulo, valor, help="Último valor disponível no SGS")
                st.plotly_chart(estilo(fig, "", 240).update_layout(showlegend=False), width="stretch")

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
                                     marker=dict(size=5), connectgaps=False,
                                     line=dict(width=2, color=COR_CANDIDATO.get(candidato, CINZA)),
                                     hovertemplate="%{y:.2f}"))
        if coluna == "tom_medio":
            fig.add_hline(y=0, line_color=CINZA, line_width=1)
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
  O intervalo de 95% dos gráficos é `CAR ± 1,96·σ·√L`, convertido para variação %.
- Observações de estimação que caem na janela de outro evento são descartadas.
- **Limitações:** poucos eventos, eventos e notícias sobrepostos, choques globais no mesmo dia,
  e correlação temporal não é causalidade.
""")

st.divider()
st.caption(AVISO)
