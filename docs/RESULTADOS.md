# Resultados detalhados

> Parte do projeto [eleicoes-mercado](../README.md). Versão final: execução de 13/11/2026,
> com a base fechada (dados até 13/11/2026). As seções do 1º turno mantêm os números publicados
> em 23/10/2026, antes do 2º turno, como manda o pré-registro.

*** p<0,01 · ** p<0,05 · * p<0,10 · n.s. não significativo. Leitura descritiva, não causal.

## 2º turno de 2026 — análise pré-registrada

Evento #2: domingo, 25/10/2026, 17h; dia 0 = segunda, 26/10. Análise feita exatamente como
fixada em [`PRE_REGISTRO.md`](../PRE_REGISTRO.md) (tag `pre-registro-2turno`, 23/10/2026).
Todas as janelas estão completas. No USD/BRL, CAR > 0 = real **mais fraco**.

### Janela diária [-1,+3] pregões (23/10 a 29/10) — família principal

| Ativo | Modelo | CAR | Erro-padrão | t | p-valor | | Holm |
|---|---|---:|---:|---:|---:|:-:|---:|
| Ibovespa | mercado global — EEM (β=0,13) | −17,28% | 2,24 p.p. | −8,49 | <0,0001 | *** | <0,0001 |
| Real — USD/BRL (Yahoo) | BRL − controles | +7,44% | 1,36 p.p. | 5,28 | <0,0001 | *** | <0,0001 |
| Banco do Brasil ON | mercado (β=1,27) | −12,88% | 2,84 p.p. | −4,85 | <0,0001 | *** | <0,0001 |
| Vale ON | mercado (β=0,80) | +13,82% | 3,20 p.p. | 4,04 | 0,0001 | *** | 0,0003 |
| Itaú Unibanco PN | mercado (β=1,19) | +2,74% | 2,03 p.p. | 1,33 | 0,186 | n.s. | 0,372 |
| Petrobras PN | mercado (β=0,43) | −2,41% | 3,73 p.p. | −0,65 | 0,514 | n.s. | 0,514 |
| *Real — USD/BRL (BCB), checagem* | BRL − controles | +4,78% | 1,23 p.p. | 3,80 | 0,0002 | *** | — |

**Resultado confirmatório:** pelo critério pré-registrado (p < 0,05 bicaudal, Holm sobre as seis
hipóteses), há retorno anormal significativo no **Ibovespa, no real, no Banco do Brasil e na
Vale**; **Itaú e Petrobras** não diferem do previsto. O dólar do BCB confirma o do Yahoo.

Preços brutos, para referência: o Ibovespa caiu 13,9% em 26/10 (205.083 → 176.608 pontos) e o
dólar do BCB subiu 9,2% (5,0377 → 5,5007), enquanto o EEM ficou estável (−0,3%) e as moedas de
controle quase não se moveram (MXN −0,5%, ZAR +0,3%).

### Janela horária [-2h,+6h] (sexta 15h–16h e segunda 10h–15h, horário de Brasília)

| Ativo | CAR | t | p-valor | |
|---|---:|---:|---:|:-:|
| Ibovespa (média constante) | −14,81% | −12,55 | <0,0001 | *** |
| Vale ON | +18,19% | 11,46 | <0,0001 | *** |
| Banco do Brasil ON | −11,19% | −7,08 | <0,0001 | *** |
| Itaú Unibanco PN | +3,98% | 4,06 | <0,0001 | *** |
| Petrobras PN | +3,69% | 2,05 | 0,041 | ** |
| Real — USD/BRL (Yahoo) | +10,45% | 17,64 | <0,0001 | *** |

Secundária pelo pré-registro: mostra que a reação se concentra na abertura de segunda. Itaú e
Petrobras, não significativos na janela diária, são significativos na horária: o movimento
relativo das primeiras horas não persistiu até 29/10.

### Robustez — janela diária [-1,+3]

P-valores bicaudais. Placebo com 202 datas por ação (188 no `BRL=X`) na versão principal e
~870–910 na versão "qualquer dia"; o menor p-valor empírico possível é 1/203 ≈ 0,005.

| Ativo | t (principal) | Patell | BMP | Corrado | Placebo | Placebo (qualquer dia) |
|---|---:|---:|---:|---:|---:|---:|
| Ibovespa | <0,0001 | <0,0001 | 0,251 | 0,035 | 0,005 | 0,001 |
| Real — USD/BRL (Yahoo) | <0,0001 | <0,0001 | 0,341 | 0,294 | 0,005 | 0,001 |
| Banco do Brasil ON | <0,0001 | 0,014 | 0,516 | 0,741 | 0,010 | 0,008 |
| Vale ON | 0,0001 | **0,056** | 0,569 | 0,730 | 0,005 | 0,001 |
| Itaú Unibanco PN | 0,186 | 0,489 | 0,535 | 0,588 | 0,123 | 0,125 |
| Petrobras PN | 0,514 | 0,681 | 0,609 | 0,531 | 0,453 | 0,448 |
| Real — USD/BRL (BCB) | 0,0002 | 0,0002 | 0,624 | 0,730 | 0,010 | 0,005 |

**Onde os testes discordam (regra 7 do pré-registro):**

- **Vale:** significativa pelo t, pelo placebo (nas duas versões) e pelo Holm, mas **não** pelo
  Patell a 5% (p = 0,056). O Patell corrige o erro de previsão, que é grande num dia em que o
  Ibovespa (a referência do modelo) cai 14%: o AR da Vale depende de extrapolar o β para um
  movimento do índice muito fora da amostra de estimação.
- **BMP e Corrado** só rejeitam no Corrado do Ibovespa (0,035). Como no 1º turno, era esperado:
  o BMP usa 5 SAR (4 graus de liberdade) e o Corrado tem estatística limitada quando a reação se
  concentra num único dia. São checagens de volatilidade inflada, não testes com poder aqui.
- O placebo coloca Ibovespa, Vale e real fora de toda a distribuição de 202 datas sem evento.

### Sensibilidade de janela

| Ativo | [0,0] | [0,+1] | [-1,+3] (principal) | [-5,+5] |
|---|---:|---:|---:|---:|
| Ibovespa | −13,85% *** | −14,41% *** | −17,28% *** | −19,12% *** |
| Vale ON | +17,22% *** | +15,27% *** | +13,82% *** | +8,98% * |
| Banco do Brasil ON | −14,58% *** | −14,51% *** | −12,88% *** | −10,39% ** |
| Petrobras PN | −2,10% n.s. | −3,93% * | −2,41% n.s. | −7,39% n.s. |
| Itaú Unibanco PN | +3,07% *** | +2,39% * | +2,74% n.s. | +3,02% n.s. |
| Real — USD/BRL (Yahoo) | +6,91% *** | +6,36% *** | +7,44% *** | +7,00% *** |
| Real — USD/BRL (BCB) | +7,78% *** | +4,41% *** | +4,78% *** | +5,70% *** |

Ibovespa, Banco do Brasil e real têm o mesmo sinal e significância em todas as janelas. A Vale
perde força em [-5,+5] (p < 0,10): parte do ganho relativo se desfez até 03/11. Itaú é
significativo só no dia 0. A [-5,+5] atravessa Finados (02/11, sem pregão na B3) e o fim do
horário de verão americano (01/11), como previsto no pré-registro.

### Análises adicionais (Fase 2)

**Carteiras long-short** (estatal − privada; CAR > 0 = a estatal foi melhor):

| Carteira | Freq. | CAR | t | p (t) | Patell | BMP | Corrado | Placebo |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Banco do Brasil − Itaú | diária | −15,20% | −5,33 | <0,0001 | 0,007 | 0,510 | 0,949 | 0,005 |
| Petrobras − PRIO | diária | −3,34% | −0,99 | 0,327 | 0,422 | 0,321 | 0,229 | 0,429 |
| Banco do Brasil − Itaú | horária | −14,58% | −8,28 | <0,0001 | 0,039 | 0,732 | 0,065 | 0,002 |
| Petrobras − PRIO | horária | −2,68% | −1,61 | 0,108 | 0,411 | 0,814 | 0,483 | 0,112 |

**Volatilidade e volume** (média na janela [-1,+3] contra o normal; dia 0 = 26/10):

| Ativo | Volatilidade: média na janela | dia 0 | p | Volume: média na janela | dia 0 | p |
|---|---:|---:|---:|---:|---:|---:|
| Ibovespa | +371% | +39.495% | 0,0002 | +163% | +411% | <0,0001 |
| Petrobras PN | +233% | +5.240% | 0,011 | +83% | +258% | 0,0007 |
| Vale ON | +56% | +1.764% | 0,287 | +126% | +424% | <0,0001 |
| Itaú Unibanco PN | +307% | +19.169% | 0,0007 | +116% | +495% | <0,0001 |
| Banco do Brasil ON | +518% | +91.062% | <0,0001 | +314% | +1.083% | <0,0001 |
| Real — USD/BRL (Yahoo) | +646% | +24.068% | <0,0001 | — | — | — |

Os saltos de abertura de 26/10 fazem a variância realizada do dia 0 chegar a centenas de vezes
a normal; o volume do Banco do Brasil foi ~12 vezes o normal. Como no 1º turno, volatilidade e
volume são persistentes, o que deixa o t otimista; o tamanho do efeito é o número informativo.

**Juros (Tesouro Direto):** omitidos, como registrado antes da votação (desvio 5 do
pré-registro: fonte inacessível).

### Exploratório: ações adicionais e modelo multifatorial

Fora do plano confirmatório (desvios 8–9 do pré-registro); não entram no Holm.

| Ativo | CAR diário [-1,+3] | p (t) | p (Patell) | β | CAR horário |
|---|---:|---:|---:|---:|---:|
| Magazine Luiza ON | −40,33% *** | <0,0001 | 0,0008 | 2,10 | −39,60% *** |
| MRV ON | −33,46% *** | <0,0001 | <0,0001 | 1,57 | −30,05% *** |
| Cogna ON | −27,50% *** | <0,0001 | <0,0001 | 1,58 | −21,36% *** |
| Bradesco PN | −12,34% *** | <0,0001 | <0,0001 | 1,20 | −8,29% *** |
| Sabesp ON | −1,29% n.s. | 0,659 | 0,593 | 1,28 | −6,05% *** |
| Petrobras ON | −1,80% n.s. | 0,665 | 0,743 | 0,41 | +4,79% ** |
| Spread Petrobras ON − PN | +0,63% n.s. | 0,515 | 0,864 | −0,02 | +1,06% * |
| Eletrobras ON (AXIA3) | +4,57% * | 0,081 | 0,552 | 1,35 | −2,46% ** |
| Cemig PN | +5,04% ** | 0,021 | 0,100 | 1,03 | +2,77% *** |

- As maiores quedas relativas ficaram com varejo, construção e educação (setores domésticos e
  sensíveis a juros), que caíram muito além do que o β alto já previa para um dia de −14% do
  índice. A queda de 58% da MGLU3 em 26/10 foi conferida e é real (ver `DECISOES.md`).
- **Multifatorial:** com o Brent no modelo, a Petrobras PN vai de −2,41% para +0,30% e a ON de
  −1,80% para +1,24% (ambas n.s.; o Brent explica R² de 0,07 → 0,52). A Vale quase não muda
  (+13,82% → +13,44%, ***; o minério acrescenta 0,01 ao R²).

### Dólar implícito no bitcoin

No 2º turno, o dólar implícito (BTCBRL ÷ BTCUSDT) subiu **10,3%** entre o fim da votação e
segunda às 10h (z = +16,9; o maior desvio dos 311 fins de semana do placebo). Na série horária
do Yahoo, o `BRL=X` ainda não tinha se movido até 10h (+0,2% no fim de semana): o salto só
aparece na barra das 10h às 11h, de modo que, desta vez, o bitcoin antecipou praticamente toda
a reação do câmbio. O volume de bitcoin na janela foi de 309 BTC, cerca de três vezes um fim de
semana comum (mediana de 98). A tabela com todos os eventos está na seção
[Dólar implícito no bitcoin](#dólar-implícito-no-bitcoin-1).

### Leitura (descritiva, não causal)

- No pregão seguinte ao 2º turno, o mercado brasileiro teve uma reação forte e na direção
  oposta à do 1º turno: Ibovespa −17% anormal em cinco pregões, real ~5–7% mais fraco que os
  pares emergentes, Banco do Brasil abaixo e Vale acima do previsto pelo índice.
- Os movimentos são específicos do Brasil: EEM e moedas de controle ficaram estáveis no mesmo
  dia, então os modelos de retorno normal quase não descontam nada.
- Nas ações, o AR é relativo ao Ibovespa: num dia de −14% do índice, a Vale (exportadora, com
  receita em dólar) caiu bem menos do que o β previa, e o Banco do Brasil caiu bem mais.
- O estudo mede preços; nenhuma leitura é feita em termos de candidatos.

## 1º turno de 2026 — estudo principal

Execução de 23/10/2026, com dados até 22/10/2026 (números publicados antes do 2º turno e
mantidos sem alteração). Evento #1, 04/10/2026 17h; dia 0 = segunda, 05/10. Na base final, CAR,
t e p-valor do 1º turno são idênticos; só os p-valores do placebo mudam na 3ª casa, porque as
datas que tocam a janela do 2º turno passaram a ser excluídas do sorteio.

### Janela diária [-1,+3] pregões (02/10 a 08/10)

| Ativo | Modelo | CAR | Erro-padrão | t | p-valor | |
|---|---|---:|---:|---:|---:|:-:|
| Ibovespa | mercado global — EEM (β=0,13) | +10,72% | 2,25 p.p. | 4,52 | <0,0001 | *** |
| Vale ON | mercado (β=0,91) | −11,69% | 3,32 p.p. | −3,74 | 0,0003 | *** |
| Banco do Brasil ON | mercado (β=1,30) | −7,42% | 2,78 p.p. | −2,77 | 0,0066 | *** |
| Petrobras PN | mercado (β=0,33) | +7,40% | 4,04 p.p. | 1,76 | 0,0805 | * |
| Itaú Unibanco PN | mercado (β=1,15) | −0,03% | 1,96 p.p. | −0,01 | 0,9886 | n.s. |
| Real — USD/BRL (Yahoo) | BRL − controles | −2,82% | 1,37 p.p. | −2,09 | 0,0392 | ** |
| Real — USD/BRL (BCB) | BRL − controles | −2,66% | 1,30 p.p. | −2,08 | 0,0401 | ** |

### Janela horária [-2h,+6h] (sexta 15h–16h e segunda 10h–15h, horário de Brasília)

| Ativo | CAR | t | p-valor | |
|---|---:|---:|---:|:-:|
| Ibovespa (média constante) | +9,96% | 7,39 | <0,0001 | *** |
| Vale ON | −6,93% | −5,04 | <0,0001 | *** |
| Petrobras PN | +2,66% | 1,32 | 0,187 | n.s. |
| Itaú Unibanco PN | +0,62% | 0,65 | 0,519 | n.s. |
| Banco do Brasil ON | +0,05% | 0,04 | 0,969 | n.s. |
| Real — USD/BRL (Yahoo) | −4,19% | −9,18 | <0,0001 | *** (janela parcial, 7 de 8 barras) |

*** p<0,01 · ** p<0,05 · * p<0,10 · n.s. não significativo.

**Leitura (descritiva, não causal):**

- No pregão seguinte ao 1º turno, o Ibovespa subiu cerca de 7,4% em um dia (8,1% só na
  primeira hora). Isso está muito fora da variação típica do período, e as frequências diária e
  horária concordam.
- O movimento dos emergentes não explica a alta: descontado o EEM (que subiu 1,6% em 05/10), o
  CAR do Ibovespa fica em +10,7%, praticamente igual aos +10,5% do modelo de média constante.
  O β contra o EEM é baixo (0,13 na estimação; 0,32 no ano todo) em parte porque o Ibovespa
  está em reais: quando os emergentes caem, o real tende a se desvalorizar e amortece a queda.
- O real se valorizou: o USD/BRL caiu cerca de 4,5% em 05/10. Descontado o movimento médio de
  MXN, CLP, COP e ZAR, sobra um retorno anormal de −2,7% a −2,8% na janela diária. O resultado
  é o mesmo com o dólar do Yahoo e com o do BCB.
- Nas ações, o retorno anormal mede o desempenho **relativo ao Ibovespa**. Vale e Banco do
  Brasil subiram bem menos do que o modelo de mercado previa para um dia de alta forte do
  índice. Petrobras ficou acima do previsto, com significância só marginal. Itaú acompanhou o
  índice.
- Parte do CAR do Ibovespa (+2,6%) ocorreu na sexta, 02/10, **antes** do evento. Pode refletir
  antecipação (pesquisas de véspera, por exemplo) ou outros fatores; o desenho do estudo não
  separa essas explicações.

**Pré-registro do 2º turno:** antes da votação, o plano de análise do 2º turno (janelas,
modelos, testes, nível de significância e testes adicionais) foi fixado em
[`PRE_REGISTRO.md`](../PRE_REGISTRO.md) e congelado na tag `pre-registro-2turno`.

## Carteiras long-short no 1º turno

Estatal − privada do mesmo setor; CAR > 0 = a estatal foi
melhor que a privada, além do previsto pelo mercado.

| Carteira | Freq. | CAR | t | p (t) | Patell | BMP | Corrado | Placebo |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Banco do Brasil − Itaú | diária | −7,39% | −2,43 | 0,017 | 0,018 | 0,439 | 0,666 | 0,015 |
| Petrobras − PRIO | diária | +4,15% | 1,15 | 0,252 | 0,349 | 0,401 | 0,518 | 0,338 |
| Banco do Brasil − Itaú | horária | −0,56% | −0,37 | 0,712 | 0,620 | 0,435 | 0,511 | 0,660 |
| Petrobras − PRIO | horária | +5,84% | 3,07 | 0,002 | 0,021 | 0,334 | 0,514 | 0,011 |

Na sensibilidade, Banco do Brasil − Itaú é −0,5% (n.s.) em [0,0] e −8,7% (***) em [0,+1]: a
diferença aparece a partir do 2º pregão. Petrobras − PRIO é +4,2% (***) em [0,0], mas não
significativo em [-1,+3] e [-5,+5]: a diferença do dia 0 não persiste na janela.

## Volatilidade e volume no 1º turno

Média na janela [-1,+3] contra o normal; dia 0 = 05/10.

| Ativo | Volatilidade: média na janela | dia 0 | p | Volume: média na janela | dia 0 | p |
|---|---:|---:|---:|---:|---:|---:|
| Ibovespa | +220% | +8.825% | 0,005 | +118% | +262% | <0,0001 |
| Petrobras PN | +128% | +2.239% | 0,079 | +59% | +204% | 0,009 |
| Vale ON | +102% | +154% | 0,104 | +131% | +308% | <0,0001 |
| Itaú Unibanco PN | +280% | +7.515% | 0,001 | +124% | +328% | <0,0001 |
| Banco do Brasil ON | +558% | +8.211% | <0,0001 | +222% | +558% | <0,0001 |
| Real — USD/BRL (Yahoo) | +187% | +4.992% | 0,003 | — | — | — |

No dia 0, a variância realizada de quase todos os ativos foi dezenas de vezes a normal, por
causa do salto de abertura depois do fim de semana do 1º turno; o volume do Ibovespa e das ações
ficou de três a quase sete vezes o normal. Volatilidade e volume são persistentes, o que torna o
t otimista; o tamanho do efeito é o número mais informativo.

## Ações adicionais e spread ON − PN no 1º turno de 2026

Modelo de mercado; exploratório.

| Ativo | CAR diário [-1,+3] | p (t) | p (Patell) | β | CAR horário |
|---|---:|---:|---:|---:|---:|
| Magazine Luiza ON | +11,33% n.s. | 0,151 | 0,196 | 2,08 | +2,65% n.s. |
| Cogna ON | +8,88% * | 0,059 | 0,055 | 1,55 | −1,67% n.s. |
| Petrobras ON | +8,88% * | 0,062 | 0,092 | 0,32 | +2,49% n.s. |
| Sabesp ON | +7,95% ** | 0,012 | 0,016 | 1,24 | +2,72% * |
| Bradesco PN | +3,95% * | 0,051 | 0,114 | 1,17 | +4,76% *** |
| MRV ON | +3,02% n.s. | 0,605 | 0,597 | 1,57 | +0,32% n.s. |
| Spread Petrobras ON − PN | +1,38% n.s. | 0,169 | 0,115 | −0,02 | −0,17% n.s. |
| Cemig PN | −1,73% n.s. | 0,419 | 0,559 | 1,02 | −1,42% n.s. |
| Eletrobras ON (AXIA3) | −4,95% * | 0,051 | 0,074 | 1,34 | −1,93% n.s. |

São nove testes a mais: com 10% de nível, um ou dois "*" seriam esperados só pelo acaso.

## Modelo de mercado simples × multifatorial (Ibovespa + commodity)

CAR diário [-1,+3].

| Ação | Evento | Simples | Multifatorial | β do fator (p) | R² simples → multi |
|---|---|---:|---:|---:|---:|
| PETR4 | 2014 · 1º | +6,53% ** | +6,55% ** | 0,00 (0,980) | 0,77 → 0,77 |
| PETR4 | 2014 · 2º | −13,41% *** | −13,38% *** | 0,08 (0,592) | 0,82 → 0,82 |
| PETR4 | 2018 · 1º | +5,07% n.s. | +5,29% n.s. | 0,04 (0,846) | 0,45 → 0,45 |
| PETR4 | 2018 · 2º | −6,06% n.s. | −5,92% n.s. | 0,05 (0,781) | 0,48 → 0,48 |
| PETR4 | 2022 · 1º | +1,77% n.s. | +1,55% n.s. | 0,19 (0,003) | 0,37 → 0,42 |
| PETR4 | 2022 · 2º | −18,08% *** | −18,13% *** | 0,22 (0,001) | 0,39 → 0,45 |
| PETR4 | 2026 · 1º | +7,40% * | +3,90% n.s. | 0,39 (<0,0001) | 0,03 → 0,58 |
| PETR3 | 2026 · 1º | +8,88% * | +4,95% n.s. | 0,44 (<0,0001) | 0,03 → 0,57 |
| VALE3 | 2014 · 1º | −5,62% * | −5,86% ** | 0,14 (0,191) | 0,21 → 0,22 |
| VALE3 | 2014 · 2º | −14,05% *** | −14,21% *** | 0,17 (0,135) | 0,18 → 0,19 |
| VALE3 | 2022 · 2º | −1,37% n.s. | +0,79% n.s. | 0,29 (0,0003) | 0,44 → 0,51 |
| VALE3 | 2026 · 1º | −11,69% *** | −11,44% *** | 0,22 (0,199) | 0,29 → 0,30 |

(A tabela completa, com todos os eventos e a PETR3, está no dashboard e em
`fct_modelo_multifatorial`.)

**Leitura:**

- **Petrobras em 2026:** o Brent explica a maior parte da variação da ação no período de
  estimação (R² de 0,03 para 0,58). Descontado o petróleo, o CAR do 1º turno cai de +7,4% para
  +3,9% e deixa de ser significativo: parte do que o modelo simples chamava de anormal acompanhou
  o petróleo.
- **Petrobras em 2014 e 2018:** o Brent quase não muda nada (β ≈ 0), e os resultados dos dois
  modelos coincidem.
- **Vale:** o minério de ferro acrescenta pouco ao R² (de 0 a +0,07), coerente com a fragilidade
  da série `TIO=F` (ver [`DECISOES.md`](../DECISOES.md)). As conclusões sobre a Vale não mudam.

## Eleições de 2014 a 2026 — CAR diário [-1,+3]

Mesma metodologia em todos os eventos.

| Ativo | 2014 · 1º | 2014 · 2º | 2018 · 1º | 2018 · 2º | 2022 · 1º | 2022 · 2º | 2026 · 1º | 2026 · 2º |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Ibovespa | +5,47% ** | +0,13% n.s. | +2,71% n.s. | +2,88% n.s. | +6,28% *** | −0,55% n.s. | +10,72% *** | −17,28% *** |
| Petrobras PN | +6,53% ** | −13,41% *** | +5,07% n.s. | −6,06% n.s. | +1,77% n.s. | −18,08% *** | +7,40% * | −2,41% n.s. |
| Vale ON | −5,62% * | −14,05% *** | −5,52% n.s. | +1,46% n.s. | −1,30% n.s. | −1,37% n.s. | −11,69% *** | +13,82% *** |
| Itaú Unibanco PN | −0,83% n.s. | +5,64% *** | +0,51% n.s. | −2,28% n.s. | −2,42% n.s. | +0,26% n.s. | −0,03% n.s. | +2,74% n.s. |
| Banco do Brasil ON | +12,68% *** | +4,17% n.s. | +6,38% * | −1,09% n.s. | −3,32% n.s. | −1,82% n.s. | −7,42% *** | −12,88% *** |
| Real — USD/BRL (Yahoo) | −3,75% * | −3,16% n.s. | −2,55% n.s. | −0,98% n.s. | −3,18% n.s. | −5,89% *** | −2,82% ** | +7,44% *** |
| Real — USD/BRL (BCB) | −3,37% n.s. | −2,92% n.s. | −4,23% ** | −0,82% n.s. | −3,45% * | −5,05% ** | −2,66% ** | +4,78% *** |

O 2º turno de 2026 tem o maior CAR em módulo do Ibovespa e do real (Yahoo) em todo o período,
nos dois casos com sinal oposto ao de todos os eventos anteriores com reação significativa (no
dólar do BCB, o maior em módulo continua sendo o do 2º turno de 2022, −5,05%).

## Análise agregada entre eleições

Todos os 8 eventos; p-valores bicaudais.

| Ativo | CAAR | CAR > 0 | t agregado | t transversal | qui² sem direção |
|---|---:|---:|---:|---:|---:|
| Ibovespa | +0,97% | 6/8 | 0,250 | 0,765 | <0,0001 |
| Petrobras PN | −2,82% | 4/8 | 0,082 | 0,446 | <0,0001 |
| Vale ON | −3,36% | 2/8 | 0,0086 | 0,303 | <0,0001 |
| Itaú Unibanco PN | +0,42% | 4/8 | 0,574 | 0,668 | 0,130 |
| Banco do Brasil ON | −0,70% | 3/8 | 0,565 | 0,814 | <0,0001 |
| Real — USD/BRL (Yahoo) | −1,93% | 1/8 | 0,011 | 0,206 | <0,0001 |
| Real — USD/BRL (BCB) | −2,26% | 1/8 | 0,0012 | 0,074 | <0,0001 |

Por turno (dashboard e `fct_caar_eventos`):

- **1º turnos (4):** Ibovespa +6,3% (4 de 4 positivos), real −3,1% (4 de 4 com o real mais forte
  que os pares), Vale −6,1%. Sem mudança: o 2º turno de 2026 não entra neste grupo.
- **2º turnos (4):** Ibovespa −4,1% (2 de 4 positivos; t agregado p = 0,0007, mas t transversal
  p = 0,47, porque o resultado vem quase todo de 2026). A Petrobras tem CAAR de −10,2% (0 de 4
  positivos; t transversal p = 0,072). O real tem CAAR de −0,8%: três 2º turnos com o real mais
  forte e o de 2026 com o real bem mais fraco.

**Leitura (descritiva):** a análise agregada distingue duas coisas. Primeiro, se há reação
anormal em qualquer direção: o qui-quadrado rejeita para Ibovespa, Petrobras, Vale, Banco do
Brasil e real, e o 2º turno de 2026 reforça isso. Segundo, se a reação vai sempre para o mesmo
lado: até o 1º turno de 2026, o real tinha se valorizado contra os pares nas 7 eleições e o
Ibovespa tinha subido em 6 de 7; o 2º turno de 2026 quebrou as duas regularidades. Com 8
eventos, o CAAR com sinal só segue robusto (t agregado e transversal a 10%) para o real do BCB;
o do Ibovespa vai a +1,0% (n.s.). A conclusão que sobrevive é que eleições presidenciais
costumam mover o mercado brasileiro de forma anormal, **mas a direção depende de cada eleição**.

## Dólar implícito no bitcoin

USD/BRL; negativo = real mais forte.

| Evento | Sexta 17h → domingo (pré) | Domingo → segunda 10h (reação) | z da reação | p empírico | Fim de semana: implícito × oficial |
|---|---:|---:|---:|---:|---:|
| 2022 · 1º turno | −0,09% | −1,94% | −3,4 | 0,019 | −2,02% × — |
| 2022 · 2º turno | −0,49% | +1,32% | +2,3 | 0,048 | +0,83% × — |
| 2026 · 1º turno | +1,02% | −4,42% | −7,8 | 0,003 | −3,45% × −4,28% |
| 2026 · 2º turno | −0,46% | +10,32% | +16,9 | 0,003 | +9,82% × +0,20% |

Placebo com 311 fins de semana (base final); desvio-padrão da reação num fim de semana comum:
0,58%. Em 2022 não há barras de 1h do `BRL=X` para comparar (o Yahoo só guarda ~2 anos). No 2º
turno de 2026, o `BRL=X` horário só se moveu depois das 10h (ver a seção do 2º turno), por isso o
oficial do fim de semana fica em +0,2%.

- No 1º turno de 2026, o dólar implícito caiu 4,4% entre o fim da votação e a abertura de
  segunda. É o menor p-valor possível com 309 fins de semana, e o movimento tem a mesma direção
  e ordem de grandeza da queda do câmbio oficial no fim de semana (−4,3%). Boa parte da
  reação do real já aparecia no bitcoin antes de o mercado oficial abrir.
- O volume de bitcoin na janela da reação (84 BTC) ficou perto do de um fim de semana comum
  (mediana de 98 BTC): o sinal veio do preço, sem um aumento de liquidez que o tornasse mais
  confiável.

## Robustez do 1º turno — janela diária [-1,+3]

P-valores bicaudais.

| Ativo | t (principal) | Patell | BMP | Corrado | Placebo | Placebo (qualquer dia) | Holm |
|---|---:|---:|---:|---:|---:|---:|---:|
| Ibovespa | <0,0001 | <0,0001 | 0,226 | 0,128 | 0,005 | 0,001 | <0,0001 |
| Vale ON | 0,0003 | 0,0010 | 0,116 | 0,022 | 0,005 | 0,001 | 0,0015 |
| Banco do Brasil ON | 0,0066 | 0,0055 | 0,243 | 0,125 | 0,015 | 0,016 | 0,026 |
| Petrobras PN | 0,081 | 0,135 | 0,342 | 0,146 | 0,075 | 0,059 | 0,161 |
| Itaú Unibanco PN | 0,989 | 0,913 | 0,960 | 0,726 | 0,995 | 0,989 | 0,989 |
| Real — USD/BRL (Yahoo) | 0,039 | 0,039 | 0,581 | 0,946 | 0,048 | 0,030 | 0,118 |
| Real — USD/BRL (BCB) | 0,040 | 0,040 | 0,628 | 0,914 | 0,055 | 0,042 | — |

Placebo com 200 datas elegíveis por ação (186 no `BRL=X`) na versão principal e ~870 na versão
"qualquer dia"; com 200 datas, o menor p-valor empírico possível é 1/201 ≈ 0,005.

## Sensibilidade de janela do 1º turno

CAR e significância pelo t principal.

| Ativo | [0,0] | [0,+1] | [-1,+3] (principal) | [-5,+5] |
|---|---:|---:|---:|---:|
| Ibovespa | +7,56% *** | +7,17% *** | +10,72% *** | +14,16% *** |
| Vale ON | −7,39% *** | −8,22% *** | −11,69% *** | −14,24% *** |
| Banco do Brasil ON | +0,80% n.s. | −5,06% *** | −7,42% *** | −4,19% n.s. |
| Petrobras PN | +5,51% *** | +2,70% n.s. | +7,40% * | +13,01% ** |
| Itaú Unibanco PN | +1,32% n.s. | +3,93% *** | −0,03% n.s. | +2,64% n.s. |
| Real — USD/BRL (Yahoo) | −4,13% *** | −4,38% *** | −2,82% ** | −4,46% ** |
| Real — USD/BRL (BCB) | −4,35% *** | −4,61% *** | −2,66% ** | −4,56% ** |

**Leitura da robustez:**

- **Ibovespa e Vale** são significativos em todos os testes que têm poder para isso: t, Patell,
  placebo nas duas versões e Holm; na horária, o placebo também dá o menor p-valor possível. O
  CAR do Ibovespa fica fora de toda a distribuição placebo.
- **Banco do Brasil** continua significativo com Patell, placebo e Holm (p = 0,026), mas o sinal
  depende da janela: o CAR do próprio dia 0 é positivo e não significativo; a reação relativa
  negativa aparece de +1 em diante.
- **Real:** significativo a 5% pelo t, por Patell e pelo placebo "qualquer dia" (0,030 e 0,042);
  no placebo principal fica no limite (0,048 no Yahoo, 0,055 no BCB). É muito significativo nas
  janelas curtas ([0,0] e [0,+1]) e não sobrevive ao ajuste de Holm na janela principal (0,118):
  o CAR da janela principal (−2,8%) é menor que o dos dois primeiros dias (−4,4% em [0,+1]).
- **Petrobras** segue marginal (p ≈ 0,06–0,16 na janela principal), significativa só em [0,0]
  e [-5,+5]. **Itaú** não difere do previsto, salvo em [0,+1].
- **BMP e Corrado quase nunca rejeitam**, e isso era esperado: o BMP usa só os 5 SAR da janela
  (4 graus de liberdade) e o Corrado, com uma reação concentrada num único dia, tem estatística
  máxima de ~1,7/√5 por dia de choque. Eles servem como checagem de casos em que o t seria
  inflado por volatilidade alta, não como teste com poder para um choque de um dia.
