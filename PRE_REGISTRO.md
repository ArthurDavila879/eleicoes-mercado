# Pré-registro — 2º turno das eleições de 2026

Este documento fixa, **antes do resultado**, como será analisada a reação do mercado ao
2º turno. Foi escrito em 23/10/2026, antes da votação, e está congelado na tag anotada
`pre-registro-2turno`. Não contém nenhum dado nem resultado do 2º turno.

O estudo é neutro: as hipóteses são bicaudais (não preveem direção), não citam candidatos e
usam exatamente a mesma metodologia aplicada ao 1º turno. Qualquer desvio deste plano será
registrado na seção **Desvios** no fim do arquivo, com data e justificativa, sem apagar o texto
original (o histórico do git e a tag permitem conferir).

## 1. Evento

| | |
|---|---|
| Evento | 2º turno: encerramento da votação e início da divulgação oficial dos resultados pelo TSE (`evento_id` 2 em `data/eventos.csv`) |
| Data e hora | domingo, **25/10/2026, 17h** de Brasília (20h UTC) — Res. TSE 23.751/2026, votação das 8h às 17h em todo o país |
| Dia 0 (diário) | **segunda-feira, 26/10/2026** (1º pregão a partir do evento) |
| Barra 0 (horária) | 1ª barra de 1h de 26/10/2026 (abertura da B3, 10h de Brasília = 13h UTC) |
| Fuso de referência | `America/Sao_Paulo` (UTC−3, sem horário de verão) |

Como a votação termina num domingo, o retorno do dia/barra 0 inclui todo o intervalo desde o
fechamento de sexta, 23/10. A hora usada é a do início da divulgação (única hora oficial e
verificável), e não a hora da definição matemática do resultado; como o mercado está fechado no
domingo, isso não muda o dia nem a barra 0.

## 2. Ativos

Os mesmos do 1º turno (`dbt/seeds/ativos.csv`):

| Ativo | Fonte | Modelo de retorno normal |
|---|---|---|
| Ibovespa (`^BVSP`) | Yahoo | diário: modelo de mercado global contra o ETF `EEM`; horário: média constante |
| Petrobras PN, Vale ON, Itaú Unibanco PN, Banco do Brasil ON | Yahoo | modelo de mercado contra o Ibovespa |
| Real — USD/BRL (`BRL=X`) | Yahoo | BRL − média das moedas de controle (MXN, CLP, COP, ZAR; mín. 2) |
| Real — USD/BRL (BCB/SGS série 1) | BCB | idem, só diário (checagem de robustez entre fontes) |

Ativos adicionais da Fase 2 (seção 6): carteiras long-short Banco do Brasil ON − Itaú
Unibanco PN e Petrobras PN − PetroRio ON (`PRIO3`), volatilidade e volume anormais, e taxas do
Tesouro Direto.

## 3. Janelas e estimação (análise principal, já implementada)

| | Diária | Horária |
|---|---|---|
| Janela do evento | **[-1, +3] pregões** = 23/10 a 29/10/2026 | **[-2h, +6h]** = barras −2…+5 (sexta 23/10 15h e 16h; segunda 26/10 10h a 15h, Brasília) |
| Janela de estimação | [-120, -11] pregões, mín. 60 | [-300, -11] barras, mín. 150 |
| Exclusão | observações da estimação dentro da janela [-1,+3]/[-2h,+6h] do 1º turno são descartadas | idem |

As janelas contam observações do próprio ativo (pregões/barras), não tempo de relógio. Feriados
e ausência de cotação seguem as regras já documentadas em `DECISOES.md`.

## 4. Testes e nível de significância

**Hipóteses (para cada ativo × frequência):**

- H0: o retorno anormal acumulado na janela do evento é zero (CAR = 0).
- H1: há retorno anormal acumulado significativo, **em qualquer direção** (CAR ≠ 0).

**Teste principal (já implementado):** `t = CAR / (σ̂·√L)`, σ̂ estimado na janela de estimação
(SQR/(n−2) no modelo de mercado; variância amostral nos demais), L = nº de retornos anormais na
janela; p-valor **bicaudal** pela t de Student com os graus de liberdade da estimação.

- **Nível de significância: 5% (bicaudal).** As marcações `*` (10%), `**` (5%) e `***` (1%)
  continuam sendo exibidas, mas só p < 0,05 será descrito como "significativo".
- **Família principal:** janela diária [-1,+3] dos seis ativos de fontes distintas (Ibovespa,
  PETR4, VALE3, ITUB4, BBAS3, `BRL=X`). Além dos p-valores individuais, será reportado o ajuste
  de **Holm** para essas seis comparações. O dólar do BCB é checagem da mesma hipótese do
  `BRL=X` e fica fora da família.
- **Análise horária:** confirmatória/secundária (mostra quando, dentro do pregão, a reação ocorre).
- **Janelas parciais:** mesma regra atual — p-valor calculado com pelo menos metade das
  observações esperadas; o status `janela_parcial` é exibido.
- Os resultados serão reportados **para todos os ativos e testes**, significativos ou não.

## 5. Testes adicionais de robustez (Fase 1)

Calculados para cada evento × ativo × frequência, com os mesmos parâmetros e a mesma janela de
estimação do teste principal. São adicionais: não substituem nem alteram o teste principal.
Valem igualmente para o 1º e o 2º turno.

1. **Patell (1976)** — AR padronizado com correção do erro de previsão:
   `SAR_t = AR_t / (σ̂·√C_t)`, com `C_t = 1 + 1/T + (Rm_t − R̄m)² / Σ(Rm_τ − R̄m)²` nos modelos de
   mercado (Rm = retorno de referência, T = nº de observações da estimação); `C_t = 1 + 1/T` na
   média constante; `C_t = 1` no modelo de controle de moedas (nenhum parâmetro de média é
   estimado). Estatística `Z = Σ SAR_t / √(L·(T−k)/(T−k−2))`, k = nº de parâmetros, comparada à
   normal padrão (bicaudal).
2. **BMP (Boehmer, Musumeci e Poulsen, 1991)** — robusto a aumento de variância no evento. A
   versão original usa a dispersão **entre empresas** dos SAR; aqui cada evento × ativo é um caso
   único (N = 1), então será usada a adaptação em série temporal: variância dos SAR estimada
   **dentro da janela do evento**, `t_BMP = (Σ SAR_t / √L) / dp(SAR_t na janela)`, com L − 1 graus
   de liberdade. Só é calculado com L ≥ 3 (não existe em [0,0] nem [0,+1]). Tem pouco poder com
   L = 5; é reportado como verificação, não como teste principal.
3. **Corrado (1989)** — teste de postos não paramétrico. Postos `K_t` dos AR na amostra combinada
   estimação + janela do evento (N observações); `S(K) = √( (1/N) Σ (K_t − (N+1)/2)² )`;
   estatística `Σ_{t∈janela} (K_t − (N+1)/2) / (√L·S(K))`, normal padrão (bicaudal).
4. **Placebo / bootstrap** — para cada ativo e frequência, a mesma metodologia (mesmo modelo,
   mesmas janelas de estimação e de evento) aplicada a datas sem evento:
   - **N = 1000** datas sorteadas sem reposição, **semente fixa 20261025**;
   - a janela do pseudoevento não pode tocar a janela [-1,+3]/[-2h,+6h] de nenhum evento real;
     observações da estimação dentro dessas janelas são descartadas, como no estudo real;
   - o pseudodia/pseudobarra 0 é sorteado entre posições equivalentes à do evento real: o
     **1º pregão após um dia sem pregão** (diário) e a **1ª barra de um pregão** (horário), porque
     o retorno do dia/barra 0 real inclui um fim de semana. Uma versão sem essa restrição
     (qualquer pregão/barra) será reportada como sensibilidade;
   - histórico: diário desde 01/01/2023 (coletado só para o placebo; não altera as janelas de
     estimação dos eventos reais, que caem em 2026); horário, o máximo que o Yahoo fornece
     (cerca de 730 dias);
   - se houver menos datas elegíveis que N, usam-se **todas** as elegíveis e o número é reportado;
   - p-valor empírico bicaudal: `(1 + #{|CAR_placebo| ≥ |CAR_real|}) / (1 + n_placebo)`.
5. **Sensibilidade de janela (diária):** CAR e p-valor (teste principal) em **[0,0], [0,+1],
   [-1,+3] e [-5,+5]**, com a mesma estimação [-120,-11]. A janela principal continua
   [-1,+3]. Para o 2º turno, a [-5,+5] vai de 19/10 a 03/11/2026 (02/11, Finados, sem pregão na
   B3) e atravessa o fim do horário de verão americano (01/11): nos dois últimos pregões o
   fechamento da NYSE passa a ser às 18h de Brasília, o que desalinha levemente o EEM do Ibovespa.

## 6. Análises adicionais (Fase 2)

Todas com hipóteses bicaudais, mesmas janelas e mesma estimação do teste principal:

1. **Carteiras long-short de mesmo setor:** `r = r_BBAS3 − r_ITUB4` e `r = r_PETR4 − r_PRIO3`
   (log-retornos), tratadas como mais um ativo, com modelo de mercado contra o Ibovespa (o β
   captura a exposição residual ao mercado). H0: CAR da carteira = 0. A carteira mede a diferença
   de reação entre empresas de controle estatal e privado do mesmo setor; não é interpretada como
   avaliação de candidato.
2. **Volatilidade anormal:** volatilidade realizada diária `RV_d = Σ r_h²` das barras de 1h do
   pregão (inclui a barra de abertura, que carrega o intervalo desde o fechamento anterior).
   Anormal = `ln RV_d − média(ln RV)` na estimação [-120,-11], padronizado pelo desvio-padrão da
   estimação; acumulado na janela [-1,+3]; H0: volatilidade anormal acumulada = 0.
3. **Volume anormal** (Ibovespa e ações; moedas não têm volume no Yahoo): `ln(1+V_t) −
   média(ln(1+V))` na estimação [-120,-11], padronizado e acumulado como na volatilidade.
4. **Juros (Tesouro Direto, dados abertos do Tesouro Transparente):** variação diária, em
   pontos-base, da taxa de compra da manhã de um título **prefixado** (LTN, vencimento mais próximo de
   3 anos a partir do evento) e de um **IPCA+** (NTN-B Principal, vencimento mais próximo de 10
   anos), entre os que têm taxa em todos os dias da estimação e da janela. Modelo de média
   constante; AR = Δtaxa − média(Δtaxa) na estimação; CAR e t como no teste principal. Se a fonte
   não for acessível de forma confiável, esta análise será omitida e isso será registrado.

## 7. Regras de leitura

- "Significativo" = p < 0,05 no teste principal. Os testes de robustez são reportados ao lado;
  se discordarem do principal, isso será dito explicitamente, sem escolher o teste mais favorável.
- Um CAR significativo indica movimento incomum em torno do evento, não causalidade.
- Nenhuma conclusão será formulada em termos de candidatos; a leitura é sobre preços.
- O GDELT continua apenas descritivo e não entra em testes.
- Os números do 1º turno já publicados no README não mudam: tudo o que é novo é adicional.

## Desvios

*(nenhum até o momento)*
