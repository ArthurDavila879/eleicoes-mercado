"""Dashboard Streamlit: reação do mercado brasileiro a eventos das eleições de 2026.

Rodar: ``streamlit run app.py`` (porta 8501). Lê o DuckDB gerado por ``python -m src.pipeline``.
Tema escuro em ``.streamlit/config.toml``; cada tela do menu lateral abre com uma explicação.
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

# Paleta categórica de ordem fixa, nos tons validados para superfície escura; a cor segue a entidade.
PALETA = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"]
CINZA = "#8a8f98"
# Alta/baixa: cores de estado (sempre acompanhadas do sinal e do valor, nunca só a cor)
COR_ALTA = "#0ca30c"
COR_BAIXA = "#d03b3b"
COR_ATIVO = {
    "^BVSP": PALETA[0], "PETR4.SA": PALETA[1], "VALE3.SA": PALETA[2], "ITUB4.SA": PALETA[3],
    "BBAS3.SA": PALETA[4], "BRL=X": PALETA[5], "BCB_DOLAR": PALETA[6], "EEM": PALETA[7],
}
# Candidatos: cores sem associação partidária (laranja e água), atribuídas em ordem alfabética
COR_CANDIDATO = {c: cor for c, cor in zip(sorted(config.CANDIDATOS_2_TURNO), [PALETA[1], PALETA[2]])}
NOMES_STATUS = {
    "completo": "completo",
    "janela_parcial": "janela parcial",
    "aguardando_dados": "aguardando dados",
    "estimacao_insuficiente": "estimação insuficiente",
}
NOMES_MODELO = {
    "mercado": "modelo de mercado (Ibovespa)", "mercado_global": "mercado global (EEM)",
    "media_constante": "média constante", "controle_moedas": "BRL − média controles",
}
# Nomes curtos para os cards do painel (os nomes completos estão no seed de ativos)
NOME_CARD = {"BRL=X": "Dólar (Yahoo)", "BCB_DOLAR": "Dólar (BCB)", "EEM": "Emergentes (EEM)",
             "ITUB4.SA": "Itaú PN", "BBAS3.SA": "Banco do Brasil"}
# Ativos do painel de cards, na ordem de exibição
ATIVOS_PAINEL = ["^BVSP", "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBAS3.SA", "BRL=X", "BCB_DOLAR", "EEM"]
# Formato do preço no hover, por classe de ativo (Ibovespa em pontos, ações em R$, moedas com 4 casas)
FORMATO_PRECO = {"indice": "%{customdata:,.0f} pts", "acao": "R$ %{customdata:,.2f}",
                 "indice_global": "US$ %{customdata:,.2f}"}
FORMATO_PRECO_PADRAO = "%{customdata:,.4f}"
Z_95 = 1.959964

TELAS = {
    "painel": ":material/dashboard: Painel",
    "evento": ":material/bolt: Reação ao evento",
    "tempo": ":material/show_chart: Ativos no tempo",
    "real": ":material/currency_exchange: Real × emergentes",
    "noticias": ":material/newspaper: Notícias (GDELT)",
    "metodo": ":material/menu_book: Metodologia",
}

ESTILO = f"""
<style>
/* Cards dos ativos */
div[class*="st-key-card_"] {{
    background: #1d2026; border: 1px solid #2a2e36; border-radius: 12px;
    padding: 14px 16px 10px 16px; gap: 0.25rem;
}}
div[class*="st-key-card_"]:hover {{ border-color: #3a404b; }}
.card-topo {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }}
.card-nome {{ font-weight: 700; font-size: 1.05rem; line-height: 1.2; }}
.card-ticker {{ color: {CINZA}; font-size: 0.78rem; }}
.card-preco {{ text-align: right; font-weight: 600; font-size: 0.98rem; white-space: nowrap; }}
.selo {{ display: inline-block; margin-top: 3px; padding: 1px 7px; border-radius: 6px;
         font-size: 0.8rem; font-weight: 700; }}
.selo-alta {{ background: rgba(12,163,12,0.18); color: #3fd13f; }}
.selo-baixa {{ background: rgba(208,59,59,0.20); color: #ff6b6b; }}
.selo-neutro {{ background: rgba(138,143,152,0.18); color: #c3c6cc; }}
.card-rodape {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }}
.card-rodape div {{ background: #16181d; border-radius: 6px; padding: 4px 6px; text-align: center;
                    font-size: 0.74rem; color: {CINZA}; line-height: 1.25; }}
.card-rodape div {{ white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.card-rodape b {{ display: block; color: #e6e7e9; font-size: 0.8rem; }}
.card-nome, .card-ticker {{ white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
/* Caixa de explicação no topo de cada tela */
.explica {{ background: rgba(25,195,125,0.07); border-left: 3px solid #19c37d; border-radius: 6px;
            padding: 10px 14px; margin: 4px 0 18px 0; font-size: 0.9rem; color: #c9ccd1; }}
.explica b {{ color: #e6e7e9; }}
/* Menu lateral em formato de navegação */
section[data-testid="stSidebar"] div[role="radiogroup"] label {{
    padding: 7px 10px; border-radius: 8px; margin-bottom: 2px; width: 100%;
}}
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{ background: #262a31; }}
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {{
    background: rgba(25,195,125,0.14);
}}
section[data-testid="stSidebar"] label[data-testid="stRadioOption"] > div > div:first-child:not([data-testid]) {{
    display: none;
}}
</style>
"""


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


# ---------------- Formatação ----------------
def fmt_num(valor: float, casas: int = 2) -> str:
    """Número no padrão brasileiro: 130.512,34."""
    return f"{valor:,.{casas}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def fmt_pct(valor: float, casas: int = 1) -> str:
    return ("+" if valor >= 0 else "−") + fmt_num(abs(valor), casas) + "%"


def fmt_preco(valor: float, classe: str) -> str:
    if classe == "indice":
        return f"{fmt_num(valor, 0)} pts"
    if classe == "indice_global":
        return f"US$ {fmt_num(valor, 2)}"
    if classe == "moeda_brasil":
        return f"R$ {fmt_num(valor, 4)}"
    return f"R$ {fmt_num(valor, 2)}"


def selo(variacao: float | None) -> str:
    if variacao is None or pd.isna(variacao):
        return '<span class="selo selo-neutro">—</span>'
    classe = "selo-alta" if variacao > 0 else "selo-baixa" if variacao < 0 else "selo-neutro"
    return f'<span class="selo {classe}">{fmt_pct(variacao, 2)}</span>'


def rotulo_curto(ev) -> str:
    """'1º turno' a partir de '1º turno: encerramento...'; cai no #id se não houver prefixo."""
    prefixo = str(ev["descricao"]).split(":")[0].strip()
    return prefixo if len(prefixo) <= 25 else f"#{ev['evento_id']}"


# ---------------- Gráficos ----------------
def marcar_eventos(fig: go.Figure, eventos: pd.DataFrame, selecionado: int | None = None,
                   janela: tuple | None = None, rotulos: bool = True) -> None:
    """Linhas verticais nos instantes dos eventos (o selecionado em destaque) e, se houver,
    a janela do evento selecionado sombreada."""
    if janela is not None:
        fig.add_vrect(x0=janela[0], x1=janela[1], fillcolor=CINZA, opacity=0.18, line_width=0, layer="below")
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
    """Layout comum: fundo transparente sobre o tema escuro, grade discreta, legenda horizontal
    no topo e separadores decimais brasileiros."""
    fig.update_layout(
        height=altura, margin=dict(l=10, r=10, t=40, b=10), hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.06, x=0, title_text=""),
        yaxis_title=titulo_y, separators=",.", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(namelength=-1),
    )
    fig.update_xaxes(showgrid=False, showline=True, linecolor="rgba(255,255,255,0.15)")
    if datas:
        fig.update_xaxes(hoverformat="%d/%m/%Y %H:%M", tickformatstops=[
            dict(dtickrange=[None, 86_400_000], value="%d/%m %Hh"),
            dict(dtickrange=[86_400_000, 2_000_000_000], value="%d/%m"),  # até ~3 semanas
            dict(dtickrange=["M1", None], value="%m/%Y"),
        ])
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.07)", zeroline=False)
    return fig


def grafico(fig: go.Figure) -> None:
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False})


def cabecalho(titulo: str, subtitulo: str, explicacao: str) -> None:
    """Título da tela e a caixa 'Como ler esta tela' (HTML simples, texto fixo do app)."""
    st.title(titulo)
    st.caption(subtitulo)
    st.markdown(f'<div class="explica"><b>Como ler esta tela.</b> {explicacao}</div>', unsafe_allow_html=True)


# =====================================================================
st.markdown(ESTILO, unsafe_allow_html=True)

if not banco_pronto():
    st.title("Eleições 2026 × mercado brasileiro")
    st.warning(AVISO)
    st.error("Banco de dados não encontrado ou incompleto. Rode `python -m src.pipeline` "
             "(ou `docker compose --profile pipeline run --rm pipeline`) e recarregue a página.")
    st.stop()

eventos = consultar("select * from staging.stg_eventos order by data_hora_utc")
ativos = consultar("select * from referencia.ativos")
nome_ativo = dict(zip(ativos["ativo"], ativos["nome"]))
classe_ativo = dict(zip(ativos["ativo"], ativos["classe"]))
resultados = consultar("select * from marts.resultados_eventos")

# ---------------- Menu lateral ----------------
with st.sidebar:
    st.markdown("### :material/how_to_vote: Eleições 2026 × Mercado")
    tela = st.radio("Tela", list(TELAS), format_func=TELAS.get, label_visibility="collapsed")
    st.divider()
    rotulos_evento = {
        int(r.evento_id): f"{rotulo_curto(r._asdict())} · {r.data_hora_local:%d/%m/%Y %H:%M}"
        for r in eventos.itertuples()
    }
    evento_id = (st.selectbox("Evento analisado", list(rotulos_evento), format_func=rotulos_evento.get)
                 if rotulos_evento else None)
    st.caption("Horários em America/Sao_Paulo (UTC−3). Fontes: BCB/SGS, Yahoo Finance, GDELT.")
    st.divider()
    st.caption(AVISO)

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


def resumo_evento() -> None:
    """Faixa com o evento selecionado e os principais números da janela diária."""
    if evento is None:
        st.info("Nenhum evento cadastrado em `data/eventos.csv`.")
        return
    with st.container(border=True):
        st.markdown(f"#### :material/event: {rotulo_curto({'descricao': evento['descricao'], 'evento_id': evento_id})}"
                    f" — {evento['data_hora_local']:%d/%m/%Y às %H:%M}")
        st.caption(f"{evento['descricao']} · [fonte]({evento['fonte_url']})")
        diario = res_evento[res_evento["frequencia"] == "diaria"].set_index("ativo")
        prontos = diario[diario["status"].isin(["completo", "janela_parcial"])]
        if prontos.empty:
            st.info("**Aguardando dados.** A janela [-1,+3] pregões deste evento ainda não aconteceu ou não foi "
                    "coletada; os resultados aparecem sozinhos depois da próxima coleta que trouxer esses pregões.")
            return
        c1, c2, c3, c4 = st.columns(4)
        for col, ativo, rotulo in [(c1, "^BVSP", "Ibovespa — CAR [-1,+3]"),
                                   (c2, "BRL=X", "Real vs. controles — CAR [-1,+3]")]:
            if ativo in prontos.index:
                linha = prontos.loc[ativo]
                col.metric(rotulo, f"{fmt_pct(linha['car_pct'])} {linha['significancia']}",
                           help=f"p-valor {fmt_num(linha['p_valor'], 4)}")
        significativos = int((prontos["p_valor"] < 0.05).sum())
        c3.metric("Ativos com p < 0,05", f"{significativos} de {len(prontos)}")
        c4.metric("Janela", "completa" if (prontos["status"] == "completo").all() else "parcial")


# =====================================================================
# Painel: cards dos ativos
# =====================================================================
def tela_painel() -> None:
    cabecalho(
        "Painel", "Visão rápida de cada ativo acompanhado no estudo.",
        "Cada card mostra o <b>último preço</b> e a <b>variação do último pregão</b> (selo verde = alta, "
        "vermelho = baixa), o gráfico dos últimos ~6 meses com o evento selecionado marcado (linha "
        "pontilhada) e, no rodapé, o <b>CAR do evento</b> (retorno anormal acumulado na janela [-1,+3] "
        "pregões, com as estrelas de significância), a variação em 30 dias e no ano. Para o dólar "
        "(USD/BRL), alta = real mais fraco. O CAR mede o quanto o ativo se moveu <b>além do esperado</b>; "
        "os detalhes estão em <i>Reação ao evento</i>.",
    )
    resumo_evento()
    st.write("")

    lista = ", ".join(f"'{a}'" for a in ATIVOS_PAINEL)
    precos = consultar(f"select ativo, cast(data as timestamp) as data, preco from staging.stg_precos_diarios "
                       f"where ativo in ({lista}) order by data")
    car_diario = res_evento[res_evento["frequencia"] == "diaria"].set_index("ativo")
    colunas = st.columns(4)
    for i, ativo in enumerate(a for a in ATIVOS_PAINEL if a in set(precos["ativo"])):
        serie = precos[precos["ativo"] == ativo].set_index("data")["preco"]
        with colunas[i % 4]:
            card_ativo(i, ativo, serie, car_diario)
    st.caption("Preços de fechamento diários (ações ajustadas por proventos). O ETF EEM (emergentes, em US$) é a "
               "referência de mercado global do Ibovespa; não tem CAR próprio.")


def card_ativo(i: int, ativo: str, serie: pd.Series, car_diario: pd.DataFrame) -> None:
    classe = classe_ativo.get(ativo, "")
    ultimo = serie.iloc[-1]
    var_dia = 100 * (ultimo / serie.iloc[-2] - 1) if len(serie) > 1 else None
    base_30 = serie[serie.index <= serie.index[-1] - timedelta(days=30)]
    var_30 = 100 * (ultimo / base_30.iloc[-1] - 1) if not base_30.empty else None
    var_ano = 100 * (ultimo / serie.iloc[0] - 1)
    car_txt = "—"
    if ativo in car_diario.index and car_diario.loc[ativo, "status"] in ("completo", "janela_parcial"):
        linha = car_diario.loc[ativo]
        car_txt = f"{fmt_pct(linha['car_pct'])} {linha['significancia']}"
    elif ativo in car_diario.index:
        car_txt = "aguardando"

    with st.container(key=f"card_{i}"):
        st.markdown(
            f'<div class="card-topo"><div><div class="card-nome">{NOME_CARD.get(ativo, nome_ativo.get(ativo, ativo))}</div>'
            f'<div class="card-ticker">{ativo} · até {serie.index[-1]:%d/%m}</div></div>'
            f'<div class="card-preco">{fmt_preco(ultimo, classe)}<br>{selo(var_dia)}</div></div>',
            unsafe_allow_html=True,
        )
        recorte = serie[serie.index >= serie.index[-1] - timedelta(days=180)]
        cor = COR_ALTA if recorte.iloc[-1] >= recorte.iloc[0] else COR_BAIXA
        fig = go.Figure(go.Scatter(x=recorte.index, y=recorte.values, mode="lines",
                                   line=dict(width=1.8, color=cor), hoverinfo="skip"))
        if evento is not None:
            fig.add_vline(x=evento["data_hora_local"], line_dash="dot", line_width=1, line_color=CINZA)
        fig.update_layout(height=110, margin=dict(l=0, r=0, t=4, b=0), showlegend=False,
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        st.plotly_chart(fig, width="stretch", config={"staticPlot": True}, key=f"spark_{ativo}")
        fmt_opc = lambda v: "—" if v is None else fmt_pct(v)  # noqa: E731
        st.markdown(
            f'<div class="card-rodape"><div>CAR<b>{car_txt}</b></div>'
            f'<div>30 dias<b>{fmt_opc(var_30)}</b></div><div>No ano<b>{fmt_opc(var_ano)}</b></div></div>',
            unsafe_allow_html=True,
        )


# =====================================================================
# Reação ao evento: CAR
# =====================================================================
def tela_evento() -> None:
    cabecalho(
        "Reação ao evento", "Estudo de evento: retornos anormais e sua significância estatística.",
        "O <b>retorno anormal</b> é o retorno observado menos o retorno <i>normal</i> previsto por um modelo "
        "estimado nos meses anteriores (ações: contra o Ibovespa; Ibovespa: contra o ETF de emergentes; real: "
        "contra a média de outras moedas emergentes). O <b>CAR</b> soma esses retornos na janela do evento. "
        "Nas barras, o traço cinza é o <b>intervalo de 95%</b>: se ele não cruza o zero, o movimento é "
        "estatisticamente incomum. As estrelas resumem o p-valor (*** muito forte, n.s. não significativo). "
        "À direita, o CAR acumulado pregão a pregão mostra <b>quando</b> a reação aconteceu.",
    )
    resumo_evento()
    frequencia = st.radio("Frequência", ["diaria", "horaria"], horizontal=True,
                          format_func={"diaria": "Diária · [-1,+3] pregões", "horaria": "Horária · [-2h,+6h]"}.get)
    filtro = res_evento[res_evento["frequencia"] == frequencia]
    completos = filtro[filtro["status"].isin(["completo", "janela_parcial"])]

    if filtro.empty:
        st.info("Selecione um evento na barra lateral.")
        return
    if completos.empty:
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
        # Rótulos sempre à direita: depois da barra de erro (CAR positivo) ou da linha do zero (negativo),
        # para não colidir com a barra de erro nem com os nomes no eixo
        for nome, v, s_, fim_ in zip(nomes, dados["car_pct"], dados["significancia"].fillna(""), lim_sup):
            fig.add_annotation(x=max(fim_, 0), y=nome, text=f"{fmt_pct(v)} {s_}", showarrow=False,
                               xanchor="left", xshift=6, font=dict(size=12))
        folga = 0.55 * max(abs(lim_inf).max(), abs(lim_sup).max())
        fig.update_xaxes(range=[min(lim_inf.min(), 0) - 0.1 * folga, max(lim_sup.max(), 0) + folga])
        fig.add_vline(x=0, line_color=CINZA, line_width=1)
        altura_car = max(380, 80 + 52 * len(dados))
        estilo(fig, "", altura_car, datas=False).update_layout(
            hovermode="closest", showlegend=False, xaxis_title="CAR (%) com intervalo de 95%",
            margin=dict(l=10, r=60, t=10, b=10))
        fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.07)")
        with col_barras:
            st.markdown("**CAR na janela do evento**")
            grafico(fig)

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
            grafico(fig)

    tabela = pd.DataFrame({
        "Ativo": filtro["nome"],
        "Modelo": filtro["modelo_retorno_normal"].map(NOMES_MODELO),
        "Janela": filtro["janela"],
        "CAR (%)": filtro["car_pct"],
        "Erro-padrão (p.p.)": filtro["erro_padrao_car"] * 100,
        "β": [fmt_num(b, 2) if m in ("mercado", "mercado_global") and pd.notna(b) else "—"
              for b, m in zip(filtro["beta"], filtro["modelo_retorno_normal"])],
        "t": filtro["estatistica_t"],
        "p-valor": filtro["p_valor"].map(
            lambda p: "—" if pd.isna(p) else "<0,0001" if p < 0.0001 else fmt_num(p, 4)),
        "Signif.": filtro["significancia"].fillna("—"),
        "Obs./esperadas": filtro["n_obs"].astype(str) + "/" + filtro["n_esperado"].astype(str),
        "Status": filtro["status"].map(NOMES_STATUS),
    }).sort_values("CAR (%)", ascending=False, na_position="last")
    st.dataframe(
        tabela, width="stretch", hide_index=True,
        column_config={c: st.column_config.NumberColumn(format="%.2f")
                       for c in ["CAR (%)", "Erro-padrão (p.p.)", "t"]},
    )
    st.caption("CAR = soma dos retornos anormais (log) na janela, exibido em variação %. Significância (t de Student, "
               "bicaudal): *** p<0,01 · ** p<0,05 · * p<0,10 · n.s. não significativo. Para o real, CAR negativo = "
               "real mais forte que os pares.")


# =====================================================================
# Ativos no tempo
# =====================================================================
def tela_tempo() -> None:
    cabecalho(
        "Ativos no tempo", "Trajetória dos preços com os eventos marcados.",
        "As séries ficam em <b>base 100</b> (todas começam em 100), para comparar ativos de escalas diferentes "
        "no mesmo eixo: 120 = alta de 20% desde o início do período. As linhas verticais são os eventos e a "
        "faixa sombreada é a janela do evento selecionado. Na visão <b>horária</b> dá para ver em que hora do "
        "pregão o movimento aconteceu. Passe o mouse para ver o preço original.",
    )
    opcoes = [a for a in ativos["ativo"] if a in COR_ATIVO]
    c1, c2 = st.columns([3, 2])
    ativos_sel = c1.multiselect("Ativos", opcoes, default=["^BVSP", "PETR4.SA", "BRL=X"],
                                format_func=lambda a: f"{nome_ativo.get(a, a)} ({a})")
    granularidade = c2.radio("Granularidade", ["Diária (todo o período)", "Horária (±10 dias do evento)"],
                             horizontal=True)
    if not ativos_sel:
        st.info("Selecione ao menos um ativo.")
        return
    lista = ", ".join(f"'{a}'" for a in ativos_sel)
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
        st.info("Sem preços para os filtros escolhidos (o EEM e o dólar do BCB só têm dados diários).")
        return
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
    grafico(estilo(fig, "Índice (base 100)", 500))


# =====================================================================
# Real × emergentes
# =====================================================================
def tela_real() -> None:
    cabecalho(
        "Real × emergentes", "O real comparado a outras moedas emergentes e as séries do Banco Central.",
        "Em cima, o dólar contra o real e contra quatro moedas emergentes (peso mexicano, chileno, colombiano e "
        "rand), em base 100: <b>subir = moeda local mais fraca</b>. A linha laranja é a média das quatro. "
        "Embaixo, a diferença entre o real e essa média: <b>abaixo de zero = o real foi melhor que os pares</b>. "
        "É a ideia do retorno anormal do real: descontar o que aconteceu com todos os emergentes. Por último, "
        "dólar, euro e Selic oficiais do Banco Central.",
    )
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
                                         fillcolor="rgba(0,131,0,0.15)", hovertemplate="%{y:.2f}%"),
                              row=2, col=1)
                fig.add_hline(y=0, line_color=CINZA, line_width=1, row=2, col=1)
                fig.update_yaxes(title_text="Real vs. controles (%)", row=2, col=1)
            marcar_eventos(fig, eventos, evento_id, janela_evento("diaria"))
            estilo(fig, "Índice (base 100)", 620 if tem_real else 420)
            fig.update_yaxes(title_text="Índice (base 100)", row=1, col=1)
            grafico(fig)

    st.subheader("Séries do Banco Central (SGS)")
    bcb = consultar("select serie_nome, cast(data as timestamp) as data, valor from staging.stg_bcb_series order by data")
    if bcb.empty:
        st.info("Sem dados do BCB.")
        return
    colunas = st.columns(3)
    titulos = {"dolar_venda": ("Dólar venda", "R$ %{y:.4f}"), "euro_venda": ("Euro venda", "R$ %{y:.4f}"),
               "meta_selic": ("Meta Selic", "%{y:.2f}% a.a.")}
    for coluna, (serie, (titulo, formato)) in zip(colunas, titulos.items()):
        parte = bcb[bcb["serie_nome"] == serie]
        if parte.empty:
            continue
        fig = go.Figure(go.Scatter(x=parte["data"], y=parte["valor"], mode="lines",
                                   line_shape="hv" if serie == "meta_selic" else "linear",
                                   line=dict(width=2, color=PALETA[0]), name=titulo, hovertemplate=formato))
        marcar_eventos(fig, eventos, evento_id, rotulos=False)
        ultimo = parte.iloc[-1]
        variacao = None if len(parte) < 2 else 100 * (ultimo["valor"] / parte.iloc[-2]["valor"] - 1)
        valor = (fmt_num(ultimo["valor"], 2) + "% a.a." if serie == "meta_selic"
                 else f"R$ {fmt_num(ultimo['valor'], 4)}")
        with coluna, st.container(key=f"card_bcb_{serie}"):
            st.markdown(
                f'<div class="card-topo"><div><div class="card-nome">{titulo}</div>'
                f'<div class="card-ticker">BCB/SGS · {ultimo["data"]:%d/%m/%Y}</div></div>'
                f'<div class="card-preco">{valor}<br>{selo(variacao) if serie != "meta_selic" else ""}</div></div>',
                unsafe_allow_html=True,
            )
            grafico(estilo(fig, "", 220).update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0)))


# =====================================================================
# Notícias (GDELT)
# =====================================================================
def tela_noticias() -> None:
    cabecalho(
        "Notícias (GDELT)", "Volume e tom da cobertura de notícias sobre os candidatos do 2º turno.",
        "O GDELT monitora notícias online. Para cada candidato usamos <b>a mesma consulta</b> "
        "(nome + notícias do Brasil). <b>Volume relativo</b> = artigos do dia ÷ média do próprio candidato "
        "(1 = dia típico; 3 = três vezes mais que o normal); compare a <b>dinâmica</b>, não os níveis entre "
        "nomes. <b>Tom médio</b>: positivo = linguagem mais positiva, negativo = mais negativa. Dias sem "
        "resposta da API aparecem como lacunas. É só descritivo: não entra no teste estatístico.",
    )
    gdelt = consultar("select * from staging.stg_gdelt order by data")
    if gdelt.empty:
        st.info("Sem dados do GDELT ainda.")
        return
    st.caption("Consultas: " + " · ".join(f"`{c}`" for c in gdelt["consulta"].unique()))
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
    grafico(estilo(fig, metrica, 460))


# =====================================================================
# Metodologia
# =====================================================================
def tela_metodo() -> None:
    cabecalho(
        "Metodologia", "Como os números das outras telas são calculados.",
        "Resumo do método do estudo de evento. A justificativa de cada escolha está em <code>DECISOES.md</code> "
        "e o passo a passo no README do repositório.",
    )
    st.markdown("""
- **Retornos:** log-retornos fechamento a fechamento (diário) e barra a barra de 1h (horário).
- **Dia/barra 0:** primeiro pregão na data do evento (ou o seguinte, se o evento ocorre a partir das 17h
  ou fora de pregão); na análise horária, a primeira barra que começa no instante do evento ou depois.
- **Retorno normal:**
  - ações: modelo de mercado `R = α + β·R_Ibovespa`, estimado por MQO em [-120, -11] pregões
    ([-300, -11] barras na análise horária);
  - Ibovespa: modelo de mercado global `R = α + β·R_EEM` (ETF de emergentes, NYSE) na análise diária,
    com o retorno do EEM medido entre os mesmos pregões do Ibovespa; na horária, média constante
    (as barras de 1h dos EUA não se alinham às da B3);
  - real (USD/BRL, Yahoo e BCB): retorno anormal = retorno do real − média de MXN, CLP, COP e ZAR.
- **CAR** = soma dos retornos anormais na janela [-1,+3] pregões ou [-2h,+6h];
  `t = CAR / (σ·√L)`, com σ estimado na janela de estimação e p-valor da t de Student.
  O intervalo de 95% dos gráficos é `CAR ± 1,96·σ·√L`, convertido para variação %.
- Observações de estimação que caem na janela de outro evento são descartadas.
- **Limitações:** poucos eventos, eventos e notícias sobrepostos, choques globais no mesmo dia,
  e correlação temporal não é causalidade.
""")


{
    "painel": tela_painel, "evento": tela_evento, "tempo": tela_tempo,
    "real": tela_real, "noticias": tela_noticias, "metodo": tela_metodo,
}[tela]()
