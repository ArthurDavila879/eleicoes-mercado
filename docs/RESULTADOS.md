# Resultados detalhados

> Parte do projeto [eleicoes-mercado](../README.md). Números da execução de 23/10/2026; os
> atualizados estão no dashboard e nas tabelas `marts.*` do DuckDB.

*** p<0,01 · ** p<0,05 · * p<0,10 · n.s. não significativo. Leitura descritiva, não causal.

## 1º turno de 2026 — estudo principal

Execução de 23/10/2026, com dados até 22/10/2026. Só o **1º turno** (evento #1,
04/10/2026 17h; dia 0 = segunda, 05/10) tem janela completa. O **2º turno** (25/10) aparece
como `aguardando_dados` e será calculado sozinho quando a coleta automática trouxer os pregões
de 26/10 em diante. Os números atualizados estão no dashboard (`marts.resultados_eventos`).

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

| Ativo | 2014 · 1º | 2014 · 2º | 2018 · 1º | 2018 · 2º | 2022 · 1º | 2022 · 2º | 2026 · 1º |
|---|---:|---:|---:|---:|---:|---:|---:|
| Ibovespa | +5,47% ** | +0,13% n.s. | +2,71% n.s. | +2,88% n.s. | +6,28% *** | −0,55% n.s. | +10,72% *** |
| Petrobras PN | +6,53% ** | −13,41% *** | +5,07% n.s. | −6,06% n.s. | +1,77% n.s. | −18,08% *** | +7,40% * |
| Vale ON | −5,62% * | −14,05% *** | −5,52% n.s. | +1,46% n.s. | −1,30% n.s. | −1,37% n.s. | −11,69% *** |
| Itaú Unibanco PN | −0,83% n.s. | +5,64% *** | +0,51% n.s. | −2,28% n.s. | −2,42% n.s. | +0,26% n.s. | −0,03% n.s. |
| Banco do Brasil ON | +12,68% *** | +4,17% n.s. | +6,38% * | −1,09% n.s. | −3,32% n.s. | −1,82% n.s. | −7,42% *** |
| Real — USD/BRL (Yahoo) | −3,75% * | −3,16% n.s. | −2,55% n.s. | −0,98% n.s. | −3,18% n.s. | −5,89% *** | −2,82% ** |
| Real — USD/BRL (BCB) | −3,37% n.s. | −2,92% n.s. | −4,23% ** | −0,82% n.s. | −3,45% * | −5,05% ** | −2,66% ** |

## Análise agregada entre eleições

Todos os eventos com dados (7); p-valores bicaudais.

| Ativo | CAAR | CAR > 0 | t agregado | t transversal | qui² sem direção |
|---|---:|---:|---:|---:|---:|
| Ibovespa | +3,89% | 6/7 | <0,0001 | 0,035 | <0,0001 |
| Petrobras PN | −2,88% | 4/7 | 0,105 | 0,503 | <0,0001 |
| Vale ON | −5,59% | 1/7 | <0,0001 | 0,047 | <0,0001 |
| Itaú Unibanco PN | +0,09% | 3/7 | 0,910 | 0,932 | 0,151 |
| Banco do Brasil ON | +1,18% | 3/7 | 0,377 | 0,656 | 0,0008 |
| Real — USD/BRL (Yahoo) | −3,20% | 0/7 | 0,0001 | 0,0013 | 0,0055 |
| Real — USD/BRL (BCB) | −3,22% | 0/7 | <0,0001 | 0,0007 | 0,0023 |

Por turno (dashboard e `fct_caar_eventos`):

- **1º turnos (4):** Ibovespa +6,3% (4 de 4 positivos), real −3,1% (4 de 4 com o real mais forte
  que os pares), Vale −6,1%.
- **2º turnos (3):** as médias se cancelam mais. A Petrobras tem CAAR de −12,7%, mas o t
  transversal dá p = 0,077 com só 3 eventos; no Ibovespa o CAAR fica perto de zero.

**Leitura (descritiva):** a análise agregada distingue duas coisas. Primeiro, se há reação
anormal em qualquer direção: o qui-quadrado rejeita para Ibovespa, Petrobras, Vale, Banco do
Brasil e real. Segundo, se a reação vai sempre para o mesmo lado: o CAAR com sinal só é robusto
(t agregado e transversal) para o Ibovespa, a Vale e o real. O real se valorizou contra os pares
emergentes na janela de **todas** as sete eleições. Com 7 eventos, o t transversal tem pouco
poder, e cada eleição continua sendo um caso com contexto próprio.

## Dólar implícito no bitcoin

USD/BRL; negativo = real mais forte.

| Evento | Sexta 17h → domingo (pré) | Domingo → segunda 10h (reação) | z da reação | p empírico | Fim de semana: implícito × oficial |
|---|---:|---:|---:|---:|---:|
| 2022 · 1º turno | −0,09% | −1,94% | −3,4 | 0,016 | −2,02% × — |
| 2022 · 2º turno | −0,49% | +1,32% | +2,3 | 0,045 | +0,82% × — |
| 2026 · 1º turno | +1,02% | −4,42% | −7,9 | 0,003 | −3,45% × −4,28% |

Placebo com 309 fins de semana; desvio-padrão da reação num fim de semana comum: 0,57%. Em 2022
não há barras de 1h do `BRL=X` para comparar (o Yahoo só guarda ~2 anos).

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
