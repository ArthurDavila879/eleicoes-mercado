# Registro de decisões

Decisões tomadas de forma autônoma durante a construção do projeto, com a justificativa.

## Ambiente
- **Python local 3.13, Docker/CI 3.12.** A máquina de desenvolvimento não tinha Python 3.12;
  o venv local usa 3.13 e a imagem Docker e o GitHub Actions usam 3.12 (versão-alvo).
  Todas as dependências fixadas em `requirements.txt` suportam 3.12.

## Fontes
- **Códigos SGS confirmados:** 1 = "Taxa de câmbio - Livre - Dólar americano (venda) - diário"
  (catálogo de dados abertos do BCB); 21619 = Euro (venda) — conferido contra a PTAX
  (boletim do BCB) de 22/10/2026 (5,6494 vs. fechamento PTAX ≈ 5,647); 432 = "Taxa de juros -
  Meta Selic definida pelo Copom" (catálogo do BCB).
- **Meta Selic (432) traz datas futuras** (a meta vigente é repetida até a próxima reunião).
  A coleta descarta datas posteriores a hoje.

## Ingestão (Etapa 2)
- **Armazenamento:** um Parquet por fonte e por mês (`data/bruto/<fonte>/<AAAA-MM>.parquet`).
  A coleta horária só reescreve o arquivo do mês corrente, o que mantém o histórico do git
  enxuto com commits automáticos de hora em hora. A deduplicação usa a chave natural
  (série/ticker/candidato + tempo) e mantém a versão mais recente; se nada mudou, o arquivo
  não é reescrito (idempotência verificada em teste).
- **Incremental com sobreposição:** cada coleta recomeça alguns dias antes do último registro
  (5 dias no diário, 3 no horário e no GDELT) para substituir barras parciais e revisões.
- **Tempo:** horários gravados em UTC sem fuso (`data_hora_utc`); datas diárias como meia-noite
  sem fuso (`data`). No diário do Yahoo, `data` é a data do pregão no fuso do próprio mercado.
- **Yahoo horário:** descartam-se linhas que não começam na hora cheia (o yfinance anexa uma
  linha "ao vivo", ex. 11:37, durante o pregão). `auto_adjust=False`; o diário guarda
  `fechamento_ajustado` (proventos), o horário não tem ajuste.
- **Falhas parciais:** uma fonte (ou ticker) com erro não derruba as demais; a coleta só
  falha se todas as fontes falharem. O BCB às vezes responde HTML/timeout: há retentativas.
- **GDELT — consulta-base:** `{termo} sourcecountry:brazil`, com a mesma regra para todos:
  nome com mais de uma palavra vira frase exata entre aspas (`"Flávio Bolsonaro"`); nome de uma
  palavra fica sem aspas (`Lula`), porque o GDELT recusa frases curtas (`"Lula"` → "The
  specified phrase is too short"). Os níveis de volume entre candidatos NÃO são diretamente
  comparáveis (nomes diferentes têm especificidades diferentes); o dashboard mostra também o
  volume relativo à média do próprio candidato.
- **GDELT — histórico:** a API DOC só pesquisa ~3 meses para trás. A primeira coleta começa em
  `hoje − 89 dias` (não em 01/01/2026); a coleta automática acumula o restante daqui em diante.
- **GDELT — limite de requisições:** 10 s entre chamadas; após uma recusa, recuo exponencial de
  30 s, 60 s e 120 s (sem espera depois da última tentativa). Se o tom falhar mas o volume vier,
  o volume é salvo e o tom já existente é preservado.
- **GDELT — recusas mesmo no ritmo pedido:** na prática a API devolve "Please limit requests to
  one every 5 seconds" até na primeira chamada após muito tempo parada (limite por IP, instável;
  provavelmente pior nos IPs compartilhados dos runners do GitHub). Por isso: (1) a falha de um
  candidato é registrada e pulada — antes abortava a fonte inteira e o candidato seguinte nem era
  tentado; a sobreposição de 7 dias recupera os dias perdidos; a fonte só falha se todos os
  candidatos falharem; (2) a CI coleta o GDELT só na rodada noturna (e na manual): o dado é
  diário, e as rodadas de hora em hora (`--fontes bcb_sgs yahoo`) só gastavam a cota.

## Eventos (Etapa 4)
- **Só dois eventos, ambos com data e hora oficiais:** o encerramento da votação e início da
  divulgação dos resultados do 1º turno (04/10/2026, 17h de Brasília) e do 2º turno
  (25/10/2026, 17h). A Res. TSE 23.751/2026 unificou o horário: votação das 8h às 17h de
  Brasília em todo o país e divulgação a partir das 17h. Fonte: notícia do TSE
  "Faltam 26 dias: votação começa e termina no mesmo horário em todo o país".
- **Por que 17h e não a hora da "definição matemática" do resultado:** o TSE não fixa hora
  para o fim da apuração e não encontrei fonte oficial acessível com o horário exato em que o
  2º turno ficou definido (o site do TSE bloqueou o acesso automatizado). Usar 17h é a única
  hora certa e verificável; como o mercado está fechado no domingo, a escolha não muda o
  dia/barra 0 (1º pregão/barra seguinte).
- **2º turno incluído mesmo sendo futuro** (hoje é 23/10/2026): a data é legalmente certa. Até
  haver dados, o resultado aparece como `aguardando_dados`; a coleta automática preenche a
  janela e o CAR passa a ser calculado sem mudanças no código.
- **Não incluí** debates, pesquisas ou declarações: exigiriam conferir data e hora em fontes
  primárias, e preferi não arriscar inventar eventos. Ficam como próximo passo.
- **Descrições neutras**, sem nomes de candidatos nem interpretação (no momento das 17h do
  1º turno ainda não se sabia quem iria ao 2º turno).
- **Validação:** `data_hora` em ISO 8601 com fuso obrigatório, tipo na lista fechada,
  descrição não vazia, URL http(s), sem duplicatas. Roda no pytest, na carga e no workflow.

## Análise (Etapa 5)
- **Correção de data das moedas no Yahoo diário (achado na carga real):** para tickers `=X`, o
  candle com data D tem fechamento ≈ abertura ≈ cotação perto de 00h em Londres, ou seja, o
  fechamento do pregão anterior. Na carga real, a queda de ~4,5% do dólar após o 1º turno
  aparecia em 06/10 no Yahoo e em 05/10 no BCB e nas barras de 1h. Cada valor diário de
  moeda é atribuído à data útil anterior da própria série (no `stg_precos_diarios`). Validação:
  a correlação dos retornos com o dólar do BCB sobe de 0,22 para 0,69, e a correlação com um
  fechamento às 17h de Brasília calculado a partir das barras de 1h é 0,96. (O BCB/SGS série 1
  é a PTAX, apurada por volta das 13h, daí a correlação menor que 1.) A correção vale
  igualmente para o real e para as moedas de controle.
- **Dia 0 diário:** 1º pregão do ativo na data do evento; se o evento é a partir das 17h
  (fechamento da B3) ou fora de pregão, o pregão seguinte. **Barra 0 horária:** 1ª barra de 1h
  que começa no instante do evento ou depois.
- **Janelas em observações do próprio ativo** (pregões/barras), não em tempo de relógio:
  "[-2h,+6h]" = 2 barras antes e 6 barras (0…+5) depois do evento. Num domingo às 17h, as barras
  -2 e -1 são as últimas da sexta e a barra 0 é a primeira do pregão seguinte, cujo retorno
  inclui o fim de semana inteiro (é aí que a reação aparece).
- **Ibovespa com modelo de mercado global (EEM), só no diário** (23/10/2026, substitui a média
  constante): `R_Ibov = α + β·R_EEM`, com o ETF iShares MSCI Emerging Markets (NYSE, USD).
  - O fechamento da NYSE (16h em Nova York) coincide com o da B3 (17h em Brasília) até o fim do
    horário de verão americano; os retornos diários são praticamente sincronizados.
  - O retorno do EEM é medido entre os **mesmos dois pregões do Ibovespa** (ASOF: último
    fechamento do ETF até cada data). Feriado só nos EUA → retorno de referência 0 naquele
    pregão; feriado só no Brasil → o pregão seguinte acumula os dias do ETF. Não se usa preço
    do ETF além do último coletado (o ASOF repetiria o preço e daria retorno 0).
  - Ibovespa em reais contra ETF em dólares: o β mistura a sensibilidade às ações emergentes e
    ao câmbio (β = 0,13 na estimação do 1º turno; 0,32 no ano). O Brasil pesa ~5% no EEM, o
    que contamina levemente a referência no próprio dia do evento (viés conservador).
  - Na análise horária o Ibovespa continua com média constante: as barras de 1h dos EUA
    começam na meia hora (13:30 UTC) e não se alinham às da B3; o EEM nem é coletado em 1h.
  - Resultado do 1º turno quase não muda: CAR de +10,72% (EEM) contra +10,50% (média constante).
- **Dólar do BCB também analisado** (ativo `BCB_DOLAR`, só diário) com o mesmo método do
  `BRL=X`, como checagem de robustez entre fontes.
- **Moedas de controle:** média simples dos log-retornos disponíveis no mesmo dia/hora,
  exigindo pelo menos 2 das 4 (as barras horárias das moedas têm lacunas de madrugada).
- **Janelas de estimação:** [-120,-11] pregões (mín. 60) e [-300,-11] barras (mín. 150), com o
  intervalo de 10 observações entre a estimação e o evento. Observações de estimação que
  caem na janela de **outro** evento são excluídas (relevante para o 2º turno, cuja janela de
  estimação contém o 1º turno).
- **Inferência:** `t = CAR/(σ̂√L)`; σ̂² = SQR/(n−2) no modelo de mercado e variância amostral
  nos demais; p-valor bicaudal pela t de Student. Não usei correção de erro de estimação nem
  testes não paramétricos (próximos passos).
- **Janelas parciais:** p-valor calculado se houver ≥ metade das observações esperadas; o
  status `janela_parcial` continua visível (acontece com moedas na madrugada de domingo).
- **p-valor num modelo Python do dbt** (scipy), porque o DuckDB não tem a distribuição t; o
  resto é SQL. Macros compartilhadas evitam duplicar a lógica entre diário e horário.
- **Schemas fixos** (`staging`, `intermediario`, `marts`, `referencia`) via `generate_schema_name`.
- **Teste de integração com dados sintéticos** (choque conhecido injetado): garante que o
  pipeline recupera o efeito com o sinal, a magnitude e a significância corretos.
- **GDELT só descritivo:** tom com 0 artigos vira nulo (indefinido). Os dados do GDELT
  vieram ralos e com lacunas (dias faltando, total monitorado oscilando de ~4 mil a ~170 mil
  artigos/dia), por isso não entram no teste estatístico.
- **Conflito de Parquet na coleta da CI:** o git não mescla binários, então um push no `main`
  durante a coleta fazia o `git pull --rebase` falhar. A CI agora guarda a própria coleta,
  volta ao `main` atualizado e mescla pelas chaves de cada fonte (`src/ingestao/mesclar.py`,
  mesma deduplicação de `salvar_incremental`, a coleta mais nova vence), com até 5 tentativas
  de push. Não refaz a coleta (o GDELT leva minutos por causa do limite de 1 requisição/5 s).

## Pré-registro do 2º turno (Fase 0, 23/10/2026)
- **`PRE_REGISTRO.md` congelado na tag `pre-registro-2turno`** antes da votação (25/10/2026,
  17h): fixa evento, ativos, janelas, modelos, testes, nível de significância (5% bicaudal) e os
  testes adicionais das fases 1–2. Hipóteses bicaudais, sem direção e sem candidatos.
- **Família principal com ajuste de Holm:** janela diária [-1,+3] dos seis ativos de fontes
  distintas; o dólar do BCB é checagem da mesma hipótese do `BRL=X` e fica fora.
- **BMP com N = 1:** a versão original usa a dispersão entre empresas, indefinida para um único
  ativo por evento; foi pré-registrada a adaptação em série temporal (dispersão dos SAR dentro
  da janela, L − 1 gl, só com L ≥ 3).
- **Placebo:** pseudodia 0 restrito ao 1º pregão após dia sem pregão (e pseudobarra 0 à 1ª
  barra do pregão), porque o dia 0 real inclui um fim de semana; histórico diário desde
  01/01/2023 para haver datas suficientes (o 2026 sozinho daria só ~70 datas elegíveis); se
  houver menos de N elegíveis, usa todas. Versão sem restrição como sensibilidade.
- **Volatilidade e volume anormais** em log, padronizados pela estimação; **Tesouro**: LTN
  ~3 anos e NTN-B Principal ~10 anos, taxa de compra da manhã, média constante.
