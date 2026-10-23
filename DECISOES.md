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

## Robustez (Fase 1, 23/10/2026)
- **Reimplementação em Python do estudo de evento** (`src/estatistica/estudo_evento.py`), usada
  pelos modelos Python do dbt de robustez. Patell, Corrado e o placebo precisam dos AR da
  estimação e de rodar o estudo em centenas de datas, o que em SQL seria uma explosão de joins.
  Para não haver duas metodologias, o teste `assert_robustez_igual_principal` exige que CAR, t,
  p-valor, nº de observações e status batam com `resultados_eventos` em todos os evento × ativo ×
  frequência (e na janela principal da sensibilidade). Os modelos SQL continuam sendo a análise
  principal e não mudaram.
- **Vars do dbt nos modelos Python:** um modelo Python só lê chaves de config com nome literal;
  as vars vão juntas numa chave `parametros_robustez` (JSON montado no `_marts.yml`). O dbt acha
  `src/` via `module_paths: [".", ".."]` no `profiles.yml`.
- **Histórico de preços desde 01/01/2023** (diário, Yahoo e BCB) e de ~720 dias nas barras de 1h:
  só com 2026 haveria ~70 datas placebo elegíveis. As janelas de estimação dos eventos reais
  caem em 2026; conferido que `resultados_eventos` ficou idêntico (diferenças < 1e-15). A coleta
  completa sozinha o histórico anterior ao 1º registro de cada série (tolerância de 7 dias para
  feriados); a busca local do histórico só criou arquivos de meses passados, sem tocar o mês
  corrente, para não conflitar com os commits da coleta automática.
- **Patell, k:** `k = T − graus de liberdade da estimação` (2 nos modelos de mercado; 1 na média
  constante e no controle de moedas, cuja σ² é a variância amostral). O pré-registro dizia "nº de
  parâmetros"; no controle de moedas não há parâmetro de média, mas a variância amostral desconta
  a média, então k = 1 é o coerente. Registrado em "Desvios" no `PRE_REGISTRO.md`.
- **Corrado:** postos na amostra estimação (resíduos dentro da amostra) + janela (AR fora da
  amostra), empates com posto médio.
- **Placebo:**
  - posições elegíveis: a janela do pseudoevento cabe nos dados e não toca nenhuma janela real;
    o pseudoevento precisa passar na mesma regra de p-valor do estudo real (estimação mínima e
    pelo menos metade das observações da janela);
  - "início de sessão": diário, intervalo de mais de 1 dia desde o pregão anterior; horário,
    ≥ 12 h desde a barra anterior (abertura do pregão nas ações; nas moedas, a volta depois do fim
    de semana, porque a madrugada tem lacunas curtas);
  - sorteio: embaralha as posições elegíveis com `default_rng([20261025, crc32(ativo|freq|versão)])`
    e pega as primeiras N válidas (sem reposição); com menos de N elegíveis, usa todas;
  - a distribuição de cada ativo é a mesma para todos os eventos. Enquanto o 2º turno não tem
    dia 0, sua janela ainda não é excluída; quando os dados chegarem, as datas placebo que a
    tocam saem automaticamente.
- **Família do Holm por evento** (6 hipóteses); com p-valores faltando, ajusta pelos disponíveis
  e registra o m usado (`n_familia_holm`).
- **Sensibilidade:** as janelas alternativas usam a mesma estimação [-120,-11] e excluem da
  estimação só as janelas principais [-1,+3] dos outros eventos.

## Análises adicionais (Fase 2, 23/10/2026)
- **Long-short como "preço" sintético no staging:** a razão `P_long / P_short` nos pregões (ou
  barras) em que os dois ativos têm cotação; o log-retorno da razão é exatamente
  `r_long − r_short` (teste de integração confere). Assim a carteira passa por todo o pipeline sem
  código novo: modelo de mercado contra o Ibovespa, AR, CAR, Patell/BMP/Corrado, placebo e
  sensibilidade. Pares em `dbt/seeds/carteiras.csv`.
- **PRIO3 só como ponta da carteira** (`modelo_retorno_normal = nenhum` no seed): o pré-registro
  não a lista como ativo do estudo. Nome no seed: "PRIO ON" (a PetroRio virou PRIO S.A.).
- **Dados da PRIO3 no git:** coletados localmente desde 2023, mas commitados só os meses até
  set/2026. Os arquivos de out/2026 são reescritos de hora em hora pela coleta da CI; commitá-los
  daqui geraria conflito binário no push. A próxima coleta da CI baixa o mês corrente da PRIO3
  sozinha (o ticker já está na lista). Até lá, no repositório, a carteira PETR4 − PRIO3 aparece
  como `aguardando_dados` no 1º turno; os números do README vêm da base local completa.
- **Volatilidade realizada:** variância realizada diária das barras de 1h, em log (a distribuição
  é muito assimétrica); dias com menos da metade das barras típicas do ativo são descartados
  (pregão em andamento ou lacunas). Inclui a barra de abertura com o intervalo noturno/fim de
  semana, porque o dia 0 do evento é justamente esse intervalo.
- **Volume:** `ln(1 + V)` do volume diário do Yahoo, só para ativos com volume (moedas vêm com 0).
- **Teste do nível anormal = estudo de evento com média constante** sobre a série em log,
  reaproveitando `estudo_evento.estudo` (mesmo dia 0, janelas, exclusões e mínimos). Não há
  placebo nem testes de robustez para essas medidas (não previstos no pré-registro).
- **Tesouro Direto omitido:** o CSV do Tesouro Transparente (`precotaxatesourodireto.csv`)
  respondeu HTTP 429 em todas as tentativas de 23/10/2026 (com e sem user-agent de navegador,
  com minutos de intervalo), embora a API CKAN do catálogo respondesse; o JSON
  `treasurybondsinfo.json` do Tesouro Direto responde HTTP 410. O catálogo indicava última
  atualização em 16/10, uma semana de atraso. O pré-registro previa omitir a análise nesse caso.
  Alternativas para o futuro: ANBIMA (taxas indicativas, exige cadastro) ou a curva de DI futuro
  da B3.

## Deploy e vitrine (Fase 3, 23/10/2026)
- **Banco construído pelo próprio app** (`src/banco.py`): no Streamlit Community Cloud não há
  build; o app reconstrói o DuckDB se ele faltar ou se a impressão digital (SHA-256 dos Parquet,
  `eventos.csv`, projeto dbt e `src/**/*.py`) mudou. O pipeline grava a impressão ao terminar,
  então um banco local feito com `python -m src.pipeline` não é refeito. A construção roda em
  subprocesso porque o dbt-duckdb mantém a conexão de escrita aberta no processo, o que impediria
  o app de abrir o arquivo em modo somente leitura. `st.cache_resource(ttl=600)`: uma construção
  por processo e nova verificação a cada 10 min (o hash de ~3 MB é instantâneo).
- **`module_paths` do dbt via `ELEICOES_RAIZ`** (definida pelo `src.pipeline`), com `.` e `..`
  como reserva: não depende do diretório em que o Streamlit Cloud ou o Docker rodam o processo.
- **dbt docs como página única** (`dbt docs generate --static` → `static_index.html`): não
  depende de servir `manifest.json`/`catalog.json` ao lado. Publicado por GitHub Actions + Pages;
  só roda quando o código muda (os commits de dados da coleta não disparam workflows).
- **Badges:** testes, coleta e documentação (workflows), Python 3.12 e dbt-duckdb. O screenshot
  fica como comentário no README até existir `docs/dashboard.png`.

## Confiabilidade da coleta (Fase 4, 23/10/2026)
- **Atualização em dias úteis, não em horas:** o `freshness` nativo das sources do dbt conta tempo
  corrido (daria alarme toda segunda-feira) e roda num comando à parte. Foi criado o teste
  genérico `atualizado_em_dias_uteis`: por grupo (ticker, série do BCB, candidato), conta os dias
  de segunda a sexta estritamente entre a data do último dado e hoje (em Brasília) e falha se
  passar de 2. Por grupo, e não pela tabela inteira, para pegar um único ticker parado (foi o que
  aconteceu com a PRIO3 logo na criação do teste). Feriados não são descontados: um feriado
  pode antecipar um alarme em um dia.
- **Fora do `dbt build` comum:** testes de source que falham fazem o `dbt build` pular os modelos
  que dependem da fonte, e o dashboard ficaria sem banco por causa de um ticker atrasado. Por isso
  ficam na tag `atualizacao`, excluída por `src.pipeline` no build e rodada só com
  `--verificar-atualizacao` (no workflow de coleta, depois do commit dos dados).
- **GDELT só avisa** (`severity: warn`): recusa requisições com frequência e é só descritivo.
- **Issue automática:** job `avisar_falha` (`if: failure()`, `issues: write`) com o `gh` do runner;
  procura issue aberta com o rótulo `coleta-falhou` e comenta nela, senão cria (e cria o rótulo
  se faltar).
- **Proposta pendente — tirar os commits de dados do `main`:** avaliada e entregue ao usuário
  (branch `data` separada vs. Git LFS); nada implementado até a decisão.

## Ampliação da coleta (rodada 3, bloco A, 23/10/2026)
- **Histórico diário desde 01/01/2014** (Yahoo e BCB), para as eleições de 2014, 2018 e 2022. Os
  resultados de 2026 não mudam (conferido: diferenças < 1e-15), porque as janelas de estimação são
  relativas ao evento.
- **Placebo cortado em 2023:** o pré-registro fixou o placebo no histórico desde 01/01/2023. Com
  preços desde 2014, a série do placebo é cortada nessa data (dados e estimação, e também o 1º
  retorno, que usaria o preço de 2022) — var `placebo_inicio`. Conferido: as distribuições e os
  p-valores empíricos da Fase 1 ficaram idênticos.
- **ELET3 → AXIA3:** o Yahoo não tem mais `ELET3.SA` (404). A Eletrobras passou a se chamar AXIA
  Energia; `AXIA3.SA` traz o histórico desde 2014 (o Yahoo identifica "AXIA Energia SA").
- **BTC-BRL fora do Yahoo:** `BTC-BRL` não existe no Yahoo. O dólar implícito usa a Binance
  (`BTCBRL` e `BTCUSDT`, mesma corretora e mesmo instante, API pública de dados de mercado).
  Comparada ao Mercado Bitcoin nos últimos 30 dias, a Binance teve mais liquidez no par em reais
  (mediana de 1,8 BTC/h contra 0,44). `BTC-USD` do Yahoo foi coletado como checagem cruzada. A
  Binance pode bloquear IPs de alguns países; se falhar na CI, a coleta das outras fontes segue
  e o teste de atualização da Binance só gera aviso.
- **Minério de ferro (`TIO=F`) — série consistente, mas fraca:** sem lacunas desde 2014 e sem
  preços repetidos por muitos dias (máx. 4), mas com volume zero em 97% dos dias (são preços de
  ajuste do contrato da CME, com pouco negócio). A correlação diária com a VALE3 é só 0,19
  (0,02 em 2018 e 0,04 em 2026), e a do minério do dia seguinte com a VALE3 é 0,12: o ajuste do
  minério acontece em outro horário e parte da informação aparece com um dia de defasagem. Para
  comparação, Brent × PETR4 = 0,41 no mesmo dia e ~0 defasado. O modelo VALE3 + minério é feito
  como pedido, mas deve ser lido com essa ressalva.
- **Filtro de pico isolado no Yahoo diário** (`stg_precos_diarios`): um preço que se afasta mais
  de 0,3 em log dos dois vizinhos e reverte no pregão seguinte é descartado. Em 2014–2016 o
  `COP=X` alterna valores como 2.399 e 24,25 (vírgula deslocada); sem o filtro, a média das
  moedas de controle teria saltos de ±460%. Movimentos reais grandes (PRIO3 +61% em 24/03/2016)
  não revertem e ficam.
- **Teste de plausibilidade:** limite subiu de 0,5 para 0,7 em log (o salto real da PRIO3 em 2016
  passaria de 0,5) e vale só para os ativos usados nos modelos; fatores globais e cripto ficam
  fora (o VIX sobe 77% num dia).

## Eleições anteriores e análise agregada (rodada 3, bloco B, 23/10/2026)
- **Eventos de 2014, 2018 e 2022 em `data/eventos.csv`**, hora = início da divulgação oficial
  dos resultados para presidente, cada um com fonte:
  - 2014 1º turno, 19h: Agência Câmara de 05/10/2014;
  - 2014 2º turno, 20h com Brasília em horário de verão (UTC−2): Rádio Senado de 16/10/2014;
  - 2018 1º turno, 19h: Agência Câmara de 07/10/2018;
  - 2018 2º turno, 19h: notícia do TSE (Res. 23.554, art. 239: dados de presidente só a partir
    das 17h do Acre);
  - 2022, 17h de Brasília: TSE (horário unificado, Res. 23.669).

  O fuso de 2014 com horário de verão está no próprio ISO 8601 (`-02:00`); o `stg_eventos` usa
  UTC−3 fixo só para calcular a data e a hora local, e como todos os eventos são num domingo à
  noite, o dia 0 é a segunda-feira seguinte em qualquer caso.
- **`evento_id` = ordem da linha no arquivo** (antes, ordem cronológica). Com os eventos antigos
  no fim do CSV, os de 2026 continuam com ids 1 e 2, que o pré-registro e o README citam. O
  dashboard ordena por data e abre no evento mais recente que já tem resultado.
- **Só análise diária antes de 2025** (var `inicio_analise_horaria`, teste
  `assert_eventos_antigos_so_diarios`); a volatilidade realizada (barras de 1h) também fica só
  para 2026. O volume entra para todos os anos.
- **Placebo só para eventos desde 2023:** a distribuição placebo vem de 2023–2026 e comparar com
  ela um CAR de 2014 misturaria regimes de volatilidade diferentes. Patell, BMP, Corrado,
  sensibilidade de janela e Holm valem para todos os eventos.
- **CAAR e três testes:** t agregado (variâncias da estimação, eventos independentes), t
  transversal (dispersão entre eventos, N ≥ 3) e qui-quadrado sem direção (`Σ t²`). O último foi
  incluído por neutralidade: não supõe que todas as eleições movam o preço no mesmo sentido.
  Grupos: todos, 1º turnos e 2º turnos (turno lido da descrição, "1º turno"/"2º turno").
- **Rótulo dos eventos com ano** no dashboard ("1º turno 2014"); "No ano" dos cards passou a
  contar desde o último fechamento do ano anterior (a série agora começa em 2014).

## Ações adicionais, spread e modelo multifatorial (rodada 3, bloco C, 23/10/2026)
- **Ações novas analisadas com o mesmo modelo de mercado** e todos os testes (robustez,
  placebo, sensibilidade). Ficam fora da família do Holm: são exploratórias e não estavam no
  pré-registro confirmatório. O README avisa sobre comparações múltiplas.
- **Spread PETR3 − PETR4** como carteira long-short (razão de preços, como as demais), com modelo
  de mercado; β ≈ 0, como esperado para duas classes da mesma empresa.
- **Multifatorial em Python** (`src/estatistica/multifatorial.py`): MQO com intercepto e dois
  fatores, σ² = SQR/(n − 3), t com n − 3 gl, mesmas regras de dia 0, janelas, exclusões e mínimos.
  Retorno do fator entre os mesmos dois pregões da ação (último preço do fator até cada data),
  sem usar preço além do último coletado. Teste do β do fator (p) e R² dos dois modelos na mesma
  amostra de estimação, para mostrar o ganho.
- **Só diário:** o Brent e o minério não são coletados de hora em hora, e as barras de 1h dos
  futuros americanos não se alinham às da B3.
- **Fatores definidos em `dbt/seeds/modelos_multifatoriais.csv`** (PETR4/PETR3 → `BZ=F`; VALE3 →
  `TIO=F`), lado a lado com o modelo simples de `resultados_eventos`.

## Dólar implícito no bitcoin (rodada 3, bloco D, 23/10/2026)
- **Mesma corretora e mesmo instante:** `BTCBRL / BTCUSDT` na Binance, barra a barra. Usar BTC-BRL
  de uma fonte e BTC-USD de outra misturaria a base entre corretoras com o câmbio. O `BTC-USD` do
  Yahoo entra como checagem (`dolar_implicito_yahoo`; razão média com o principal: 1,0002).
- **USDT como dólar:** a USDT oscila perto de 1 dólar; desvios pequenos entram no dólar implícito.
- **Instantes:** preço em T = fechamento da barra de 1h que termina em T. Sexta 17h de Brasília =
  20h UTC (fechamento da B3 e do câmbio); segunda 10h = 13h UTC (abertura da B3). Para o
  `BRL=X` oficial, aceita-se a última barra até 3 h antes (há lacunas de barras em horários de
  pouco negócio).
- **Placebo em vez de teste paramétrico:** os retornos de bitcoin têm caudas pesadas e a
  volatilidade de fim de semana é diferente da dos dias úteis; a distribuição empírica do mesmo
  intervalo em ~300 fins de semana (sem os dos eventos) é a referência mais honesta. z = reação /
  desvio-padrão do placebo, só descritivo.
- **Sem "retorno anormal":** a reação não desconta um movimento global do dólar no fim de semana
  (não há referência confiável de câmbio de emergentes aos domingos). O placebo mede o quanto a
  variação é incomum, não o quanto é específica do Brasil.
