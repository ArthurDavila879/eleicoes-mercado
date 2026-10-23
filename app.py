"""Dashboard Streamlit: reação do mercado brasileiro a eventos das eleições de 2026.

Rodar: ``streamlit run app.py`` (porta 8501). Lê o DuckDB gerado por ``python -m src.pipeline``;
se ele faltar ou estiver desatualizado em relação aos Parquet versionados, o próprio app o
reconstrói na inicialização (carga + dbt, sem coleta) — é o que acontece no Streamlit Community
Cloud. ``ELEICOES_SEM_CONSTRUCAO=1`` desliga a reconstrução.
Tema escuro em ``.streamlit/config.toml``; cada tela do menu lateral abre com uma explicação.
"""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import yaml

from src import banco, config
from src.estatistica import personalizado

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
    # Carteiras long-short (Fase 2): tons fora da paleta base, para não repetir as ações das pontas
    "LS_BBAS3_ITUB4": "#1fb5ad", "LS_PETR4_PRIO3": "#b5a01f",
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


def _vars_dbt() -> dict:
    """Janelas e parâmetros do estudo (vars de dbt/dbt_project.yml), para o evento personalizado."""
    with open(config.DIR_DBT / "dbt_project.yml", encoding="utf-8") as f:
        return yaml.safe_load(f)["vars"]


VARS = _vars_dbt()

TELAS = {
    "painel": ":material/dashboard: Painel",
    "evento": ":material/bolt: Reação ao evento",
    "tempo": ":material/show_chart: Ativos no tempo",
    "linha": ":material/timeline: Linha do tempo",
    "historico": ":material/history: Eleições 2014–2026",
    "personalizado": ":material/tune: Evento personalizado",
    "real": ":material/currency_exchange: Real × emergentes",
    "noticias": ":material/newspaper: Notícias (GDELT)",
    "atividade": ":material/equalizer: Volatilidade e volume",
    "robustez": ":material/verified: Robustez",
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


@st.cache_resource(ttl=600, show_spinner="Preparando o banco de dados a partir dos dados versionados "
                                         "(só quando os dados mudam; pode levar cerca de um minuto)…")
def preparar_banco(caminho: str) -> str:
    """Reconstrói o DuckDB se faltar ou estiver desatualizado (verificado a cada 10 min)."""
    if os.environ.get("ELEICOES_SEM_CONSTRUCAO") == "1":
        return "desativado"
    return banco.garantir_banco(Path(caminho))


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


def fmt_p(p: float) -> str:
    return "—" if pd.isna(p) else "<0,0001" if p < 0.0001 else fmt_num(p, 4)


def estrelas(p: float) -> str:
    if pd.isna(p):
        return ""
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else "n.s."


def com_estrelas(p: float) -> str:
    return f"{fmt_p(p)} {estrelas(p)}".strip()


def pct_de_log(car):
    """CAR em log-retorno → variação percentual aproximada."""
    return (np.exp(car) - 1) * 100


def selo(variacao: float | None) -> str:
    if variacao is None or pd.isna(variacao):
        return '<span class="selo selo-neutro">—</span>'
    classe = "selo-alta" if variacao > 0 else "selo-baixa" if variacao < 0 else "selo-neutro"
    return f'<span class="selo {classe}">{fmt_pct(variacao, 2)}</span>'


def rotulo_curto(ev) -> str:
    """'1º turno 2026' a partir de '1º turno: encerramento...' e da data; cai no #id se não
    houver prefixo curto."""
    prefixo = str(ev["descricao"]).split(":")[0].strip()
    rotulo = prefixo if len(prefixo) <= 25 else f"#{ev['evento_id']}"
    data = ev.get("data_hora_local") if hasattr(ev, "get") else None
    return f"{rotulo} {pd.Timestamp(data):%Y}" if data is not None and not pd.isna(data) else rotulo


# ---------------- Gráficos ----------------
def _intervalo_x(fig: go.Figure) -> tuple | None:
    """Menor e maior data entre os pontos já desenhados na figura."""
    valores = [pd.to_datetime(pd.Series(t.x)) for t in fig.data if t.x is not None and len(t.x)]
    if not valores:
        return None
    todos = pd.concat(valores).dropna()
    return (todos.min(), todos.max()) if len(todos) else None


def marcar_eventos(fig: go.Figure, eventos: pd.DataFrame, selecionado: int | None = None,
                   janela: tuple | None = None, rotulos: bool = True) -> None:
    """Linhas verticais nos instantes dos eventos (o selecionado em destaque) e, se houver,
    a janela do evento selecionado sombreada.

    Só marca eventos dentro do período dos dados já desenhados (linhas fora dele esticariam o
    eixo: uma série de 2026 ficaria espremida num canto entre 2014 e 2026). Em períodos longos,
    os dois turnos do mesmo ano ficam a 3 semanas um do outro e os rótulos se sobreporiam: só o
    evento selecionado leva rótulo completo e os demais anos levam só o ano.
    """
    intervalo = _intervalo_x(fig)
    if intervalo is not None:
        margem = pd.Timedelta(days=1)
        eventos = eventos[(eventos["data_hora_local"] >= intervalo[0] - margem)
                          & (eventos["data_hora_local"] <= intervalo[1] + margem)]
    longo = intervalo is not None and (intervalo[1] - intervalo[0]) > pd.Timedelta(days=150)
    if janela is not None:
        fig.add_vrect(x0=janela[0], x1=janela[1], fillcolor=CINZA, opacity=0.18, line_width=0, layer="below")
    anos_rotulados = set()
    for _, ev in eventos.sort_values("data_hora_local").iterrows():
        destaque = ev["evento_id"] == selecionado
        fig.add_vline(
            x=ev["data_hora_local"], line_width=1.5 if destaque else 1,
            line_dash="solid" if destaque else "dot", line_color=CINZA,
        )
        if not rotulos:
            continue
        ano = pd.Timestamp(ev["data_hora_local"]).year
        if destaque:
            texto = f"<b>{rotulo_curto(ev)}</b>"
        elif not longo:
            texto = rotulo_curto(ev)
        elif ano in anos_rotulados or (selecionado in set(eventos["evento_id"]) and ano == pd.Timestamp(
                eventos.loc[eventos["evento_id"] == selecionado, "data_hora_local"].iloc[0]).year):
            continue  # o ano já tem rótulo (ou é o do evento selecionado)
        else:
            texto = str(ano)
        anos_rotulados.add(ano)
        fig.add_annotation(
            x=ev["data_hora_local"], y=1, yref="paper", yanchor="bottom", showarrow=False,
            text=texto, font=dict(size=11),
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

if preparar_banco(str(config.CAMINHO_DUCKDB)) == "construido":
    consultar.clear()  # consultas em cache são do banco anterior

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
    # ?tela=<chave> na URL abre direto numa tela (links para compartilhar)
    pedida = st.query_params.get("tela")
    tela = st.radio("Tela", list(TELAS), format_func=TELAS.get, label_visibility="collapsed",
                    index=list(TELAS).index(pedida) if pedida in TELAS else 0)
    st.divider()
    rotulos_evento = {
        int(r.evento_id): f"{rotulo_curto(r._asdict())} · {r.data_hora_local:%d/%m/%Y %H:%M}"
        for r in eventos.sort_values("data_hora_utc", ascending=False).itertuples()
    }
    # Padrão: o evento mais recente que já tem resultado diário
    com_dados = set(resultados.loc[resultados["p_valor"].notna(), "evento_id"].astype(int))
    padrao = next((i for i, e in enumerate(rotulos_evento) if e in com_dados), 0)
    evento_id = (st.selectbox("Evento analisado", list(rotulos_evento), index=padrao,
                              format_func=rotulos_evento.get)
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


def periodo_em_volta(ev) -> tuple[pd.Timestamp, pd.Timestamp]:
    """~10 meses antes e ~2 meses depois do evento (o fim passa da última data, sem problema)."""
    centro = pd.Timestamp(ev["data_hora_local"]).normalize()
    return centro - timedelta(days=300), centro + timedelta(days=65)


def resumo_evento() -> None:
    """Faixa com o evento selecionado e os principais números da janela diária."""
    if evento is None:
        st.info("Nenhum evento cadastrado em `data/eventos.csv`.")
        return
    with st.container(border=True):
        st.markdown(f"#### :material/event: {rotulo_curto({'descricao': evento['descricao'], 'evento_id': evento_id, 'data_hora_local': evento['data_hora_local']})}"
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
    # No ano: desde o último fechamento do ano anterior (a série vai até 2014)
    base_ano = serie[serie.index < pd.Timestamp(year=serie.index[-1].year, month=1, day=1)]
    var_ano = 100 * (ultimo / (base_ano.iloc[-1] if not base_ano.empty else serie.iloc[0]) - 1)
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

    # Ativos ainda sem dados na janela saem da tabela (senão viram linhas de "None") e são listados abaixo
    sem_dados = filtro[filtro["car"].isna()]
    if not completos.empty:
        filtro = filtro[filtro["car"].notna()]
    tabela = pd.DataFrame({
        "Ativo": filtro["nome"],
        "Modelo": filtro["modelo_retorno_normal"].map(NOMES_MODELO).fillna("—"),
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
    if not completos.empty and not sem_dados.empty:
        st.caption("Ainda sem dados na janela: " + ", ".join(sem_dados["nome"].fillna(sem_dados["ativo"])) + ".")

    if frequencia == "diaria" and evento_id is not None:
        multi = consultar(f"select * from marts.fct_modelo_multifatorial where evento_id = {int(evento_id)} "
                          f"and p_valor is not null")
        if not multi.empty:
            st.markdown("**Modelo multifatorial (exploratório): mercado + commodity**")
            st.dataframe(pd.DataFrame({
                "Ativo": multi["ativo"].map(lambda a: nome_ativo.get(a, a)),
                "Fator": multi["fator"].map(lambda a: nome_ativo.get(a, a)),
                "CAR simples (%)": multi["car_pct_simples"],
                "p simples": multi["p_valor_simples"].map(com_estrelas),
                "CAR multifatorial (%)": multi["car_pct"],
                "p multifatorial": multi["p_valor"].map(com_estrelas),
                "β do fator": multi["beta_fator"],
                "R² simples → multi": [f"{fmt_num(a, 2)} → {fmt_num(b, 2)}"
                                       for a, b in zip(multi["r2_simples"], multi["r2_multifatorial"])],
            }), width="stretch", hide_index=True,
                column_config={c: st.column_config.NumberColumn(format="%.2f")
                               for c in ["CAR simples (%)", "CAR multifatorial (%)", "β do fator"]})
            st.caption("Retorno normal = α + β·Ibovespa + β·fator (Brent para Petrobras; minério de ferro para Vale), "
                       "com o fator medido entre os mesmos pregões da ação. O modelo de mercado simples continua "
                       "sendo o principal; a série do minério é fraca (ver DECISOES.md).")


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
    granularidade = c2.radio("Granularidade", ["Diária (1 ano em volta do evento)", "Diária (desde 2014)",
                                               "Horária (±10 dias do evento)"], horizontal=True)
    if not ativos_sel:
        st.info("Selecione ao menos um ativo.")
        return
    lista = ", ".join(f"'{a}'" for a in ativos_sel)
    if granularidade.startswith("Diária"):
        janela = janela_evento("diaria")
        filtro = ""
        if "volta" in granularidade and evento is not None:
            ini, fim = periodo_em_volta(evento)
            filtro = f"and data between '{ini:%Y-%m-%d}' and '{fim:%Y-%m-%d}'"
        precos = consultar(f"select ativo, cast(data as timestamp) as tempo, preco "
                           f"from staging.stg_precos_diarios where ativo in ({lista}) {filtro} order by data")
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

    st.subheader("Dólar implícito no bitcoin (fim de semana)")
    st.caption("USD/BRL implícito = BTCBRL ÷ BTCUSDT (Binance), 24 h por dia: mostra o real enquanto o câmbio e a "
               "B3 estão fechados. Par pouco líquido — sinal de direção, não cotação.")
    implicito = consultar(f"select * from marts.fct_dolar_implicito_eventos where evento_id = {int(evento_id)}") \
        if evento_id is not None else pd.DataFrame()
    if implicito.empty:
        st.info("Sem dólar implícito para este evento (o BTCBRL existe desde out/2020, ou o evento ainda não ocorreu).")
    else:
        linha = implicito.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Sexta 17h → domingo (pré)", fmt_pct(pct_de_log(linha["pre_evento"]), 2))
        c2.metric("Evento → segunda 10h", fmt_pct(pct_de_log(linha["reacao"]), 2),
                  help=f"z = {fmt_num(linha['z_reacao'], 1)} contra {int(linha['n_placebo'])} fins de semana")
        c3.metric("p empírico (placebo)", com_estrelas(linha["p_empirico"]))
        c4.metric("Fim de semana: oficial (BRL=X)",
                  "—" if pd.isna(linha["oficial_fim_de_semana"]) else fmt_pct(pct_de_log(linha["oficial_fim_de_semana"]), 2))
        ini = linha["sexta_utc"] - timedelta(hours=24)
        fim = linha["abertura_utc"] + timedelta(hours=12)
        caminho = consultar(
            f"select data_hora_utc + interval 1 hour + interval (-3) hour as tempo, dolar_implicito "
            f"from staging.stg_dolar_implicito_horario where data_hora_utc between '{ini}' and '{fim}' order by 1")
        oficial = consultar(
            f"select data_hora_utc + interval 1 hour + interval (-3) hour as tempo, preco from staging.stg_precos_horarios "
            f"where ativo = 'BRL=X' and data_hora_utc between '{ini}' and '{fim}' order by 1")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=caminho["tempo"], y=caminho["dolar_implicito"], mode="lines",
                                 name="Implícito (bitcoin)", line=dict(width=2, color=PALETA[1]),
                                 hovertemplate="R$ %{y:.4f}"))
        if not oficial.empty:
            fig.add_trace(go.Scatter(x=oficial["tempo"], y=oficial["preco"], mode="lines", name="Oficial (BRL=X)",
                                     line=dict(width=2, color=COR_ATIVO["BRL=X"]), hovertemplate="R$ %{y:.4f}"))
        fig.add_vline(x=evento["data_hora_local"], line_dash="dot", line_color=CINZA)
        grafico(estilo(fig, "USD/BRL", 380))
        st.caption("Horário de Brasília, no fim de cada barra de 1h. Linha pontilhada: evento.")

    st.subheader("Séries do Banco Central (SGS)")
    filtro = ""
    if evento is not None:
        ini, fim = periodo_em_volta(evento)
        filtro = f"where data between '{ini:%Y-%m-%d}' and '{fim:%Y-%m-%d}'"
        st.caption(f"De {ini:%d/%m/%Y} a {min(fim, pd.Timestamp.now()):%d/%m/%Y}, em volta do evento selecionado.")
    bcb = consultar(f"select serie_nome, cast(data as timestamp) as data, valor from staging.stg_bcb_series "
                    f"{filtro} order by data")
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
# Linha do tempo: preços, eventos e GDELT
# =====================================================================
def tela_linha() -> None:
    cabecalho(
        "Linha do tempo", "Preços, eventos e cobertura de notícias no mesmo eixo de tempo.",
        "As linhas são preços em <b>base 100</b> no início do período escolhido; as barras claras, no eixo da "
        "direita, são o <b>volume relativo de notícias</b> do GDELT por candidato (1 = dia típico do próprio "
        "candidato). As linhas verticais marcam os eventos. Serve para ver o contexto em volta de cada evento — "
        "picos de notícia, tendências anteriores —, não para tirar conclusões causais.",
    )
    opcoes = [a for a in ativos["ativo"] if a in COR_ATIVO]
    c1, c2 = st.columns([3, 2])
    selecionados = c1.multiselect("Ativos", opcoes, default=["^BVSP", "BRL=X"], key="ativos_linha",
                                  format_func=lambda a: f"{nome_ativo.get(a, a)} ({a})")
    hoje = pd.Timestamp.now().normalize()
    periodo = c2.date_input("Período", value=(hoje - pd.Timedelta(days=180), hoje), key="periodo_linha")
    if not selecionados or not isinstance(periodo, tuple) or len(periodo) != 2:
        st.info("Escolha ao menos um ativo e as duas datas do período.")
        return
    ini, fim = (pd.Timestamp(d) for d in periodo)
    lista = ", ".join(f"'{a}'" for a in selecionados)
    precos = consultar(f"select ativo, cast(data as timestamp) as tempo, preco from staging.stg_precos_diarios "
                       f"where ativo in ({lista}) and data between '{ini:%Y-%m-%d}' and '{fim:%Y-%m-%d}' order by data")
    gdelt = consultar(f"select candidato, cast(data as timestamp) as data, volume_relativo from staging.stg_gdelt "
                      f"where data between '{ini:%Y-%m-%d}' and '{fim:%Y-%m-%d}' order by data")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    for candidato, parte in gdelt.groupby("candidato"):
        fig.add_trace(go.Bar(x=parte["data"], y=parte["volume_relativo"], name=f"Notícias: {candidato}",
                             marker=dict(color=COR_CANDIDATO.get(candidato, CINZA)), opacity=0.35,
                             hovertemplate="%{y:.2f}× o normal"), secondary_y=True)
    for ativo in selecionados:
        parte = precos[precos["ativo"] == ativo]
        if parte.empty:
            continue
        fig.add_trace(go.Scatter(x=parte["tempo"], y=100 * parte["preco"] / parte["preco"].iloc[0], mode="lines",
                                 name=nome_ativo.get(ativo, ativo), line=dict(width=2, color=COR_ATIVO.get(ativo, CINZA)),
                                 hovertemplate="%{y:.1f}"), secondary_y=False)
    marcar_eventos(fig, eventos[(eventos["data_hora_local"] >= ini) & (eventos["data_hora_local"] <= fim + timedelta(days=1))],
                   evento_id)
    estilo(fig, "Preço (base 100)", 520).update_layout(barmode="overlay", bargap=0)
    fig.update_yaxes(title_text="Notícias (× dia típico)", secondary_y=True, showgrid=False, rangemode="tozero")
    grafico(fig)
    if gdelt.empty:
        st.caption("Sem dados do GDELT no período (a coleta de notícias começou em 2026).")


# =====================================================================
# Eleições 2014–2026: todos os eventos e análise agregada
# =====================================================================
def tela_historico() -> None:
    cabecalho(
        "Eleições 2014–2026", "O mesmo estudo de evento em todas as eleições presidenciais desde 2014.",
        "Cada célula é o <b>CAR diário [-1,+3]</b> de um ativo numa eleição, com a mesma metodologia (só a "
        "frequência diária: não há barras de 1h antes de 2025). Abaixo, a <b>análise agregada</b>: o CAAR é a "
        "média dos CAR; o <b>t agregado</b> e o <b>t transversal</b> testam se a média é diferente de zero; o "
        "<b>qui-quadrado sem direção</b> testa se houve reação anormal em qualquer sentido — eleições diferentes "
        "podem mover o preço para lados opostos, e a média se cancelaria.",
    )
    res = resultados[(resultados["frequencia"] == "diaria") & resultados["p_valor"].notna()].copy()
    if res.empty:
        st.info("Sem eventos com dados.")
        return
    res["evento"] = [f"{pd.Timestamp(d):%Y} · {str(desc).split(':')[0]}" for d, desc in
                     zip(res["data_hora_local"], res["descricao"])]
    ordem = res.sort_values("data_hora_local")["evento"].drop_duplicates().tolist()
    res["celula"] = [f"{fmt_pct(v, 1)} {s_}" for v, s_ in zip(res["car_pct"], res["significancia"].fillna(""))]
    principais = ["^BVSP", "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBAS3.SA", "BRL=X", "BCB_DOLAR"]
    so_principais = st.toggle("Só os ativos do estudo principal", value=True, key="historico_principais")
    if so_principais:
        res = res[res["ativo"].isin(principais)]
    larga = res.pivot(index="ativo", columns="evento", values="celula").reindex(columns=ordem)
    larga.index = [nome_ativo.get(a, a) for a in larga.index]
    st.dataframe(larga.fillna("—"), width="stretch")
    st.caption("*** p<0,01 · ** p<0,05 · * p<0,10 · n.s. não significativo (t principal). Para o real, negativo = "
               "real mais forte que os pares emergentes.")

    st.markdown("**Análise agregada entre eventos**")
    grupo = st.radio("Eventos", ["todos", "1º turno", "2º turno"], horizontal=True, key="grupo_caar",
                     format_func={"todos": "Todos", "1º turno": "Só 1º turnos", "2º turno": "Só 2º turnos"}.get)
    caar = consultar(f"select * from marts.fct_caar_eventos where grupo = '{grupo}'")
    if so_principais:
        caar = caar[caar["ativo"].isin(principais)]
    st.dataframe(pd.DataFrame({
        "Ativo": caar["ativo"].map(lambda a: nome_ativo.get(a, a)),
        "Eventos": caar["n_eventos"],
        "CAAR (%)": caar["caar_pct"],
        "CAR > 0": caar["n_positivos"].astype(str) + "/" + caar["n_eventos"].astype(str),
        "t agregado (p)": caar["p_agregado"].map(com_estrelas),
        "t transversal (p)": caar["p_transversal"].map(com_estrelas),
        "Qui² sem direção (p)": caar["p_qui2"].map(com_estrelas),
    }).sort_values("CAAR (%)"), width="stretch", hide_index=True,
        column_config={"CAAR (%)": st.column_config.NumberColumn(format="%.2f")})
    st.caption("t agregado: Σ CAR / √Σ erro-padrão², com as variâncias estimadas antes de cada evento. t transversal: "
               "média / (desvio-padrão entre eventos / √N), só com 3 ou mais eventos. Qui²: Σ t², com N graus de "
               "liberdade. Com poucos eventos, cada eleição continua sendo um caso com contexto próprio.")


# =====================================================================
# Evento personalizado
# =====================================================================
def tela_personalizado() -> None:
    cabecalho(
        "Evento personalizado", "Escolha uma data, um ativo e uma janela: o estudo de evento roda na hora.",
        "Usa <b>exatamente</b> o método do estudo: mesmo modelo de retorno normal do ativo, mesma janela de "
        "estimação, e as janelas dos eventos oficiais ficam fora da estimação. O dia 0 é o 1º pregão a partir da "
        "data (ou o seguinte, se a hora for a partir das 17h); na frequência horária, a 1ª barra a partir do "
        "instante. <b>Cuidado:</b> testar muitas datas até achar uma \"significativa\" gera falsos positivos — "
        "com 10% de nível, 1 em cada 10 datas sem nada de especial dá \"*\" por acaso.",
    )
    c1, c2, c3 = st.columns([2, 1, 2])
    data = c1.date_input("Data (horário de Brasília)", value=pd.Timestamp("2026-10-04"), key="data_pers",
                         min_value=pd.Timestamp("2014-01-01"), max_value=pd.Timestamp.now())
    hora = c2.time_input("Hora", value=pd.Timestamp("2026-10-04 17:00").time(), key="hora_pers")
    frequencia = c3.radio("Frequência", ["diaria", "horaria"], horizontal=True, key="freq_pers",
                          format_func={"diaria": "Diária", "horaria": "Horária"}.get)
    analisados = sorted(resultados.loc[resultados["frequencia"] == frequencia, "ativo"].unique(),
                        key=lambda a: nome_ativo.get(a, a))
    c4, c5, c6 = st.columns([2, 1, 1])
    ativo = c4.selectbox("Ativo", analisados, key="ativo_pers", format_func=lambda a: nome_ativo.get(a, a),
                         index=analisados.index("^BVSP") if "^BVSP" in analisados else 0)
    prefixo = "diaria" if frequencia == "diaria" else "horaria"
    unidade = "pregões" if frequencia == "diaria" else "barras de 1h"
    jan_ini = c5.number_input(f"Janela: início ({unidade})", -20, 0, int(VARS[f"janela_{prefixo}_inicio"]),
                              key=f"jan_ini_{prefixo}")
    jan_fim = c6.number_input(f"Janela: fim ({unidade})", 0, 20, int(VARS[f"janela_{prefixo}_fim"]),
                              key=f"jan_fim_{prefixo}")
    tabela = "int_retornos_diarios_ref" if frequencia == "diaria" else "int_retornos_horarios_ref"
    tabela_janelas = "int_janelas_diarias" if frequencia == "diaria" else "int_janelas_horarias"
    serie = consultar(f"select * from intermediario.{tabela} where ativo = '{ativo}'")
    reais = consultar(f"select ativo, idx, fase, evento_id from intermediario.{tabela_janelas} "
                      f"where ativo = '{ativo}' and fase = 'evento'")
    instante = pd.Timestamp.combine(pd.Timestamp(data).date(), hora)
    res, passos = personalizado.estudar(
        serie, reais, ativo, instante, frequencia, (int(jan_ini), int(jan_fim)),
        (int(VARS[f"estimacao_{prefixo}_inicio"]), int(VARS[f"estimacao_{prefixo}_fim"])),
        int(VARS[f"min_obs_estimacao_{prefixo}"]), int(VARS["hora_corte_pregao"]), int(VARS["fuso_offset_horas"]))
    if res is None:
        st.info("Sem dados para esta combinação (data futura, antes do início da série do ativo, ou sem barras "
                "de 1h nessa época — elas só existem nos últimos ~2 anos).")
        return
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("CAR", fmt_pct(pct_de_log(res["car"]), 2), help=f"t = {fmt_num(res['estatistica_t'], 2)}")
    m2.metric("p-valor (t)", com_estrelas(res["p_valor"]))
    m3.metric("Patell", com_estrelas(res["p_patell"]))
    m4.metric("Corrado", com_estrelas(res["p_corrado"]))
    m5.metric("BMP", com_estrelas(res["p_bmp"]))
    st.caption(f"Modelo: {NOMES_MODELO.get(serie['modelo_retorno_normal'].iloc[0], '—')} · estimação com "
               f"{res['n_estimacao']} observações · {res['n_obs']} de {res['n_esperado']} {unidade} na janela · "
               f"status: {NOMES_STATUS.get(res['status'], res['status'])}.")
    fig = make_subplots(specs=[[{"secondary_y": False}]])
    fig.add_trace(go.Bar(x=passos["rel"], y=passos["retorno_anormal"] * 100, name="Retorno anormal",
                         marker=dict(color=[COR_ALTA if v >= 0 else COR_BAIXA for v in passos["retorno_anormal"]],
                                     cornerradius=3), hovertemplate="%{y:.2f}%"))
    fig.add_trace(go.Scatter(x=passos["rel"], y=passos["car_acumulado"] * 100, name="CAR acumulado",
                             mode="lines+markers", line=dict(width=2, color=PALETA[0]), hovertemplate="%{y:.2f}%"))
    fig.add_vline(x=-0.5, line_dash="dot", line_color=CINZA)
    fig.add_hline(y=0, line_color=CINZA, line_width=1)
    estilo(fig, "%", 380, datas=False).update_xaxes(title=f"Posição relativa ao evento ({unidade})", dtick=1)
    grafico(fig)
    tempo = pd.to_datetime(passos["tempo"])
    tempo = (tempo.dt.strftime("%d/%m/%Y") if frequencia == "diaria"
             else (tempo + pd.Timedelta(hours=int(VARS["fuso_offset_horas"]))).dt.strftime("%d/%m/%Y %Hh"))
    st.dataframe(passos.assign(tempo=tempo, retorno_anormal=passos["retorno_anormal"] * 100,
                               car_acumulado=passos["car_acumulado"] * 100).rename(columns={
        "rel": "Posição", "tempo": "Pregão" if frequencia == "diaria" else "Início da barra (Brasília)",
        "retorno_anormal": "AR (%)",
        "car_acumulado": "CAR acumulado (%)"}), width="stretch", hide_index=True,
        column_config={c: st.column_config.NumberColumn(format="%.3f") for c in ["AR (%)", "CAR acumulado (%)"]})


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
# Volatilidade e volume
# =====================================================================
NOMES_MEDIDA = {"volatilidade_realizada": "Volatilidade realizada (barras de 1h)", "volume": "Volume negociado"}


def tela_atividade() -> None:
    cabecalho(
        "Volatilidade e volume", "O mercado ficou mais agitado do que o normal em torno do evento?",
        "Além da direção do preço, o evento pode mudar a <b>intensidade</b> dos negócios. A <b>volatilidade "
        "realizada</b> de cada dia soma os quadrados dos retornos das barras de 1h (a barra de abertura inclui o "
        "intervalo desde o fechamento anterior); o <b>volume</b> é o volume diário negociado. Os dois são "
        "comparados, em log, com a média dos meses anteriores (janela de estimação [-120,-11] pregões): "
        "<b>+100%</b> = o dobro do normal. O teste usa o acumulado na janela [-1,+3]. As moedas não têm volume "
        "no Yahoo. As carteiras long-short aparecem só na volatilidade.",
    )
    resumo_evento()
    if evento_id is None:
        return
    dados = consultar(f"select * from marts.fct_atividade_anormal where evento_id = {int(evento_id)}")
    prontos = dados[dados["p_valor"].notna()]
    if prontos.empty:
        st.info("**Aguardando dados** para este evento: os números aparecem quando a janela for coletada.")
        return
    colunas = st.columns(2)
    for coluna, (medida, parte) in zip(colunas, prontos.groupby("medida", sort=False)):
        parte = parte.sort_values("variacao_media_pct")
        nomes = [nome_ativo.get(a, a) for a in parte["ativo"]]
        fig = go.Figure(go.Bar(
            x=parte["variacao_media_pct"], y=nomes, orientation="h", width=0.55,
            marker=dict(color=[COR_ATIVO.get(a, CINZA) for a in parte["ativo"]], cornerradius=4),
            customdata=np.stack([parte["anormal_dia0_pct"], parte["p_valor"]], axis=1),
            hovertemplate="Média na janela: %{x:.0f}% acima do normal<br>Dia 0: %{customdata[0]:.0f}%"
                          "<br>p-valor %{customdata[1]:.4f}<extra>%{y}</extra>",
        ))
        for nome, v, p in zip(nomes, parte["variacao_media_pct"], parte["p_valor"]):
            fig.add_annotation(x=max(v, 0), y=nome, text=f"{fmt_pct(v, 0)} {estrelas(p)}", showarrow=False,
                               xanchor="left", xshift=6, font=dict(size=12))
        fig.add_vline(x=0, line_color=CINZA, line_width=1)
        fig.update_xaxes(range=[min(parte["variacao_media_pct"].min(), 0) * 1.1,
                                max(parte["variacao_media_pct"].max(), 0) * 1.35 + 1])
        estilo(fig, "", max(320, 80 + 48 * len(parte)), datas=False).update_layout(
            hovermode="closest", showlegend=False, xaxis_title="Média na janela [-1,+3] vs. normal (%)",
            margin=dict(l=10, r=40, t=10, b=10))
        with coluna:
            st.markdown(f"**{NOMES_MEDIDA.get(medida, medida)}**")
            grafico(fig)
    sem_dados = dados[dados["p_valor"].isna()]
    dados = dados[dados["p_valor"].notna()]
    tabela = pd.DataFrame({
        "Medida": dados["medida"].map(NOMES_MEDIDA),
        "Ativo": dados["ativo"].map(lambda a: nome_ativo.get(a, a)),
        "Média na janela (%)": dados["variacao_media_pct"],
        "Dia 0 (%)": dados["anormal_dia0_pct"],
        "t": dados["estatistica_t"],
        "p-valor": dados["p_valor"].map(com_estrelas),
        "Obs./esperadas": dados["n_obs"].fillna(0).astype(int).astype(str) + "/"
                          + dados["n_esperado"].fillna(5).astype(int).astype(str),
        "Status": dados["status"].map(NOMES_STATUS),
    })
    st.dataframe(tabela, width="stretch", hide_index=True,
                 column_config={c: st.column_config.NumberColumn(format="%.1f")
                                for c in ["Média na janela (%)", "Dia 0 (%)", "t"]})
    st.caption("Média na janela = exp(média do log anormal) − 1. Dia 0 = primeiro pregão depois do evento. "
               "Volatilidade e volume têm persistência (dias agitados vêm em sequência), o que torna o t "
               "otimista; leia junto com o tamanho do efeito.")
    if not sem_dados.empty:
        st.caption("Ainda sem dados na janela: " + ", ".join(sorted(
            {nome_ativo.get(a, a) for a in sem_dados["ativo"]})) + ".")


# =====================================================================
# Robustez
# =====================================================================
def tela_robustez() -> None:
    cabecalho(
        "Robustez", "Testes estatísticos adicionais, placebo e sensibilidade de janela.",
        "O teste principal (t) supõe retornos anormais normais e com a mesma variância de antes do evento. "
        "Aqui o mesmo CAR passa por testes que relaxam essas hipóteses: <b>Patell</b> (corrige o erro de "
        "previsão do modelo), <b>BMP</b> (usa a dispersão da própria janela, robusto a volatilidade maior no "
        "evento; precisa de ≥ 3 retornos e tem pouco poder com 5), <b>Corrado</b> (não paramétrico, por postos) "
        "e o <b>placebo</b>: a mesma conta repetida em centenas de datas <i>sem</i> evento; o p-valor empírico é "
        "a fração dessas datas com |CAR| pelo menos tão grande quanto o real. <b>Holm</b> ajusta os p-valores "
        "pelas seis comparações da família principal. Tudo foi definido antes do 2º turno em "
        "<code>PRE_REGISTRO.md</code>.",
    )
    resumo_evento()
    frequencia = st.radio("Frequência", ["diaria", "horaria"], horizontal=True, key="freq_robustez",
                          format_func={"diaria": "Diária · [-1,+3] pregões", "horaria": "Horária · [-2h,+6h]"}.get)
    if evento_id is None:
        st.info("Selecione um evento na barra lateral.")
        return
    testes = consultar(f"select * from marts.fct_testes_robustez where evento_id = {int(evento_id)} "
                       f"and frequencia = '{frequencia}'")
    placebo = consultar(f"select * from marts.fct_placebo_resultados where evento_id = {int(evento_id)} "
                        f"and frequencia = '{frequencia}'")
    prontos = testes[testes["p_valor"].notna()]
    if prontos.empty:
        st.info("**Aguardando dados** para este evento nesta frequência: os testes aparecem quando a janela "
                "do evento for coletada.")
        return

    st.markdown("**Testes de significância do CAR** (p-valores bicaudais)")
    emp = {v: placebo[placebo["versao"] == v].set_index("ativo")["p_empirico"] for v in ["restrita", "irrestrita"]}
    tabela = pd.DataFrame({
        "Ativo": prontos["ativo"].map(lambda a: nome_ativo.get(a, a)),
        "CAR (%)": pct_de_log(prontos["car"]),
        "t (principal)": prontos["p_valor"].map(com_estrelas),
        "Patell": prontos["p_patell"].map(com_estrelas),
        "BMP": prontos["p_bmp"].map(com_estrelas),
        "Corrado": prontos["p_corrado"].map(com_estrelas),
        "Placebo": prontos["ativo"].map(emp["restrita"]).map(com_estrelas),
        "Placebo (qualquer dia)": prontos["ativo"].map(emp["irrestrita"]).map(com_estrelas),
        "Holm (família)": prontos["p_valor_holm"].map(com_estrelas),
    }).sort_values("CAR (%)", ascending=False)
    st.dataframe(tabela, width="stretch", hide_index=True,
                 column_config={"CAR (%)": st.column_config.NumberColumn(format="%.2f")})
    st.caption("*** p<0,01 · ** p<0,05 · * p<0,10 · n.s. não significativo. Placebo: pseudodia 0 no 1º pregão "
               "após um dia sem pregão (ou na 1ª barra do pregão), como o evento real de domingo; "
               "'qualquer dia' sem essa restrição. Holm só na janela diária dos seis ativos da família principal.")

    st.markdown("**Placebo: distribuição do CAR em datas sem evento**")
    c1, c2 = st.columns([3, 2])
    opcoes = prontos["ativo"].tolist()
    ativo = c1.selectbox("Ativo", opcoes, format_func=lambda a: nome_ativo.get(a, a), key="ativo_placebo",
                         index=opcoes.index("^BVSP") if "^BVSP" in opcoes else 0)
    versao = c2.radio("Datas sorteadas", ["restrita", "irrestrita"], horizontal=True, key="versao_placebo",
                      format_func={"restrita": "Início de semana/pregão", "irrestrita": "Qualquer dia"}.get)
    dist = consultar(f"select car from marts.fct_placebo_distribuicao where frequencia = '{frequencia}' "
                     f"and versao = '{versao}' and ativo = '{ativo}'")
    linha = placebo[(placebo["ativo"] == ativo) & (placebo["versao"] == versao)]
    car_real = pct_de_log(float(prontos.set_index("ativo").loc[ativo, "car"]))
    if dist.empty:
        st.info("Sem datas placebo elegíveis para este ativo.")
    else:
        fig = go.Figure(go.Histogram(x=pct_de_log(dist["car"]), nbinsx=50, name="Datas sem evento",
                                     marker=dict(color=PALETA[0], line=dict(width=0)), opacity=0.85,
                                     hovertemplate="CAR %{x}<br>%{y} datas<extra></extra>"))
        fig.add_vline(x=car_real, line_color=PALETA[1], line_width=2.5)
        p_emp = linha["p_empirico"].iloc[0] if not linha.empty else np.nan
        fig.add_annotation(x=car_real, y=1, yref="paper", yanchor="bottom", showarrow=False,
                           text=f"<b>Evento: {fmt_pct(car_real)}</b> · p empírico {fmt_p(p_emp)}",
                           font=dict(color=PALETA[1], size=12))
        estilo(fig, "Nº de datas", 380, datas=False).update_layout(
            showlegend=False, hovermode="closest", bargap=0.04, xaxis_title="CAR (%) na janela")
        grafico(fig)
        st.caption(f"{len(dist)} datas sem evento, sorteadas sem reposição com semente fixa, fora das janelas dos "
                   "eventos reais, com a mesma estimação e a mesma janela do estudo.")

    if frequencia == "diaria":
        st.markdown("**Sensibilidade à janela** (diária; [-1,+3] é a principal)")
        sens = consultar(f"select * from marts.fct_sensibilidade_janelas where evento_id = {int(evento_id)}")
        sens = sens[sens["p_valor"].notna()]
        if sens.empty:
            st.info("Sem janelas com dados suficientes.")
            return
        ordem = (sens.drop_duplicates("janela").sort_values(["janela_fim", "janela_inicio"])["janela"].tolist())
        sens["celula"] = [f"{fmt_pct(pct_de_log(c), 2)} {estrelas(p)}" for c, p in zip(sens["car"], sens["p_valor"])]
        larga = sens.pivot(index="ativo", columns="janela", values="celula").reindex(columns=ordem)
        larga.index = [nome_ativo.get(a, a) for a in larga.index]
        larga.columns = [f"{j} ★" if j == "[-1,+3]" else j for j in larga.columns]
        st.dataframe(larga.fillna("—"), width="stretch")
        st.caption("CAR (%) e significância pelo teste t principal, com a mesma janela de estimação [-120,-11]. "
                   "★ janela principal.")


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
- **Carteiras long-short** (BBAS3 − ITUB4 e PETR4 − PRIO3): log-retorno da ponta comprada menos o da
  vendida, com modelo de mercado contra o Ibovespa, como mais um ativo.
- **Volatilidade e volume anormais:** log da volatilidade realizada (barras de 1h) e do volume
  diário contra a média da estimação, acumulado na janela [-1,+3].
- **Eleições de 2014, 2018 e 2022** (só diário) e **análise agregada**: CAAR, t agregado, t transversal e
  qui-quadrado sem direção (reação anormal em qualquer sentido).
- **Exploratório:** mais ações e o spread PETR3 − PETR4; modelo multifatorial (Ibovespa + Brent para Petrobras,
  Ibovespa + minério para Vale); dólar implícito no bitcoin (BTCBRL ÷ BTCUSDT) entre domingo e segunda.
- **Robustez:** testes de Patell, BMP (adaptação em série temporal) e Corrado, placebo com datas
  sem evento, sensibilidade de janela e ajuste de Holm, conforme o pré-registro (`PRE_REGISTRO.md`).
- **Limitações:** poucos eventos, eventos e notícias sobrepostos, choques globais no mesmo dia,
  e correlação temporal não é causalidade.
""")


{
    "painel": tela_painel, "evento": tela_evento, "tempo": tela_tempo, "linha": tela_linha,
    "historico": tela_historico, "personalizado": tela_personalizado,
    "real": tela_real, "noticias": tela_noticias, "atividade": tela_atividade, "robustez": tela_robustez, "metodo": tela_metodo,
}[tela]()
