# Metodologia detalhada

> Parte do projeto [eleicoes-mercado](../README.md). Números da execução de 23/10/2026; os
> atualizados estão no dashboard e nas tabelas `marts.*` do DuckDB.

O resumo do método (retornos, janelas, modelos de retorno normal e teste principal) está no
[README](../README.md#metodologia). Aqui ficam as análises adicionais.

## Robustez

Calculada para cada evento × ativo × frequência, com os mesmos parâmetros e a mesma estimação
do teste principal (fixados em [`PRE_REGISTRO.md`](../PRE_REGISTRO.md) antes do 2º turno). Os
cálculos ficam em `src/estatistica/` e rodam em modelos Python do dbt; um teste do dbt confere
que a reimplementação reproduz exatamente o CAR, o t e o p-valor dos modelos SQL.

| Teste | O que faz | Mart |
|---|---|---|
| **Patell** | AR padronizado com correção do erro de previsão do modelo (`C_t = 1 + 1/T + (Rm_t − R̄m)²/Σ(Rm − R̄m)²`); Z normal | `fct_testes_robustez` |
| **BMP** | robusto a aumento de variância no evento; como há um ativo por evento, usa a dispersão dos SAR **dentro da janela** (t com L−1 gl; só com L ≥ 3, pouco poder com L = 5) | `fct_testes_robustez` |
| **Corrado** | não paramétrico: postos dos AR na amostra estimação + janela | `fct_testes_robustez` |
| **Holm** | ajuste para as 6 comparações da família principal (janela diária de Ibovespa, PETR4, VALE3, ITUB4, BBAS3 e `BRL=X`) | `fct_testes_robustez` |
| **Placebo** | a mesma metodologia em até 1000 datas sem evento por ativo (sem reposição, semente 20261025), fora das janelas reais; p-valor empírico `(1 + #{\|CAR_placebo\| ≥ \|CAR_real\|}) / (1 + n)`. Versão principal: pseudodia 0 no 1º pregão após um dia sem pregão (ou na 1ª barra do pregão), como num evento de domingo; versão "qualquer dia" como sensibilidade | `fct_placebo_distribuicao`, `fct_placebo_resultados` |
| **Sensibilidade de janela** | CAR e p-valor (t principal) em [0,0], [0,+1], [-1,+3] (principal) e [-5,+5] pregões | `fct_sensibilidade_janelas` |

## Eleições anteriores e análise agregada (só diária)

`data/eventos.csv` traz também o 1º e o 2º turno de **2014, 2018 e 2022**, com a mesma
metodologia diária: mesmo modelo de cada ativo, janela [-1,+3] e estimação [-120,-11]. Não há
análise horária nesses anos, porque não existem barras de 1h tão antigas
(`inicio_analise_horaria`). A hora de cada evento é a do início da divulgação oficial:

- **2014 e 2018:** a divulgação para presidente só começava quando a votação terminava no Acre
  (17h locais): 19h de Brasília, ou 20h no 2º turno de 2014, com Brasília em horário de verão;
- **2022:** horário unificado, com a votação terminando às 17h de Brasília.

As fontes estão no CSV (Agência Câmara, Rádio Senado, TSE). Como todos os eventos são num
domingo à noite, o dia 0 é sempre a segunda-feira seguinte.

A análise agregada (`fct_caar_eventos`) junta os eventos de cada ativo (todos, só 1º turnos, só
2º turnos):

- **CAAR**: média dos CAR;
- **t agregado**: `Σ CAR / √Σ ep²`, com as variâncias da estimação;
- **t transversal**: média sobre o erro-padrão entre eventos, com N − 1 gl;
- **qui-quadrado sem direção**: `Σ t²`, com N gl.

O último teste é o mais neutro: eleições diferentes podem mover o preço em sentidos opostos e a
média com sinal se cancelaria; ele pergunta só se houve reação anormal, em qualquer direção.

## Dólar implícito no bitcoin (fim de semana)

O câmbio e a B3 estão fechados entre o fim da votação (domingo) e a abertura de segunda. O
bitcoin negocia 24 h por dia, então `USD/BRL implícito = BTCBRL / BTCUSDT` (Binance, barras de
1h, mesmo instante) mostra o real nesse intervalo (`fct_dolar_implicito_eventos`). As medidas
são:

- **pré-evento:** sexta 17h → domingo, no instante do evento;
- **reação:** domingo, no instante do evento → segunda 10h de Brasília (abertura da B3);
- **fim de semana inteiro:** sexta 17h → segunda 10h, comparado ao `BRL=X` oficial no mesmo
  intervalo.

A significância da reação vem de um placebo: o mesmo intervalo (domingo na hora do evento →
segunda 10h) em todos os outros fins de semana com dados. O BTCBRL existe desde out/2020, então
entram 2022 e 2026.

**Limitação de liquidez:** o par BTCBRL é pouco líquido (mediana de ~2 BTC por hora na Binance,
menos de madrugada) e tem um ágio/deságio próprio em relação ao câmbio oficial (−0,5% em média
no fim de semana do 1º turno de 2026). O dólar implícito é um sinal ruidoso, não uma cotação de
câmbio; vale como indicação de direção e de ordem de grandeza antes da abertura.

## Volatilidade e volume anormais

Na janela diária, com o mesmo dia 0 e a mesma estimação [-120,-11] (`fct_atividade_anormal`):

- **volatilidade realizada:** `ln Σ r_h²` das barras de 1h de cada dia (horário de Brasília); a barra
  de abertura inclui o intervalo desde o fechamento anterior; dias com menos da metade das barras
  típicas são descartados;
- **volume:** `ln(1 + volume diário)` (Ibovespa e ações; as moedas não têm volume no Yahoo).

O nível anormal é `x − média(x)` na estimação; o teste usa o acumulado na janela,
`t = Σ(x − média) / (dp·√L)`, que é o mesmo estudo de evento com média constante.

## Juros (Tesouro Direto) — não incluído

O plano previa medir a variação anormal das taxas de um prefixado e de um IPCA+ com os dados
abertos do Tesouro Transparente. Em 23/10/2026 o download do CSV respondeu HTTP 429 ("Muitas
requisições") em todas as tentativas, inclusive a primeira do dia, embora a API do catálogo
respondesse; o JSON antigo do site do Tesouro Direto responde HTTP 410. O arquivo também é
atualizado com cerca de uma semana de atraso. Sem fonte confiável, a análise foi omitida, como
o pré-registro previa (ver [`DECISOES.md`](../DECISOES.md)).

## Limitações

- **Poucos eventos.** Mesmo com 2014–2026 são 7 eventos com dados (8 com o 2º turno de 2026):
  pouco poder para a análise agregada transversal; cada eleição é também um estudo de caso.
- **Eleições anteriores só no diário** e com os mesmos ativos de hoje (a Eletrobras aparece como
  `AXIA3`); a composição e o peso dos ativos no índice mudaram ao longo da década.
- **Eventos sobrepostos.** Notícias, pesquisas e choques globais (juros nos EUA, commodities)
  acontecem nos mesmos dias. O controle por moedas emergentes e pelo Ibovespa reduz, mas não
  elimina, essa contaminação; a janela de 5 pregões é longa o bastante para pegar outros fatos.
- **Correlação não é causalidade.** Um CAR significativo diz que o preço se moveu de forma
  incomum em torno do evento, não que o evento causou o movimento.
- **Eventos de fim de semana.** As eleições são aos domingos às 17h; a reação aparece no
  pregão seguinte e mistura tudo o que aconteceu no intervalo.
- **Dados.** Barras horárias do Yahoo podem ter lacunas (sobretudo moedas fora do horário
  comercial) e não são ajustadas por proventos; o GDELT só pesquisa ~3 meses para trás, e o
  volume de notícias não é comparável em nível entre nomes diferentes.
- **Inferência simplificada no teste principal.** A variância do CAR ignora o erro de estimação
  dos parâmetros e supõe ARs independentes e homocedásticos; os testes de robustez (Patell, BMP,
  Corrado, placebo) relaxam essas hipóteses, mas BMP e Corrado têm pouco poder com um ativo e
  janelas curtas.
- **Dólar implícito no bitcoin** depende de um par pouco líquido (BTCBRL) e da paridade
  USDT ≈ USD; serve como sinal de direção antes da abertura, não como cotação.
- **Juros fora do estudo.** A fonte do Tesouro Direto não estava acessível de forma confiável.
- **Notícias (GDELT) com lacunas.** Em volta do 1º turno de 2026 o GDELT quase não registrou
  notícias brasileiras (dias sem dado e dias com 1–3% do volume normal); o volume de notícias
  nesses dias não reflete a cobertura real.
- **Placebo limitado pelo histórico.** Há ~200 datas elegíveis na versão principal (diária), o
  que limita a resolução do p-valor empírico (mínimo ≈ 0,005).
