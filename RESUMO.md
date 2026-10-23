# RESUMO — o que foi feito (23/10/2026)

## Entregue (um commit por etapa, testes passando em cada uma)

| Etapa | Entrega | Commit |
|---|---|---|
| 1 | Estrutura, `requirements*.txt`, `Dockerfile` (Python 3.12), `docker-compose.yml` (serviços `app` :8501, `pipeline`, `testes`), `.gitignore`, `.gitattributes`, `.dockerignore`, `CLAUDE.md` | `Etapa 1` |
| 2 | Ingestão incremental e idempotente: BCB/SGS (1, 21619, 432), yfinance diário + 1h (10 tickers), GDELT (volume + tom, mesma consulta-base para os dois candidatos), Parquet mensal em `data/bruto/`, carga no DuckDB, testes com mocks, **carga real feita** | `Etapa 2` |
| 3 | `.github/workflows/coleta.yml` (de hora em hora em dias úteis 13h05–21h05 UTC, toda noite 01h30 UTC, `workflow_dispatch`, `contents: write`, commita os Parquet) e `testes.yml` (pytest + pipeline em todo push) | `Etapa 3` |
| 4 | `data/eventos.csv` com 2 eventos verificáveis (1º e 2º turno, 17h de Brasília, fonte TSE) + validação do formato | `Etapa 4` |
| 5 | dbt-duckdb: staging → log-retornos (diário/horário) → retornos anormais → CAR + t + p-valor; 52 testes do dbt; teste de integração com choque sintético | `Etapa 5` |
| 6 | Dashboard Streamlit (ativos com eventos marcados, filtros por evento/ativo/frequência, tabela de CAR com significância, real vs. controles, séries do BCB, GDELT, aviso de não recomendação) + testes com AppTest | `Etapa 6` |
| 7 | README de portfólio (pergunta, mermaid, fontes, metodologia, resultados, limitações, como rodar e subir no GitHub) | `Etapa 7` |

## Verificação final

- `pytest -q`: **45 passed**, tanto no venv local (Python 3.13) quanto no container Docker
  (Python 3.12.15). Inclui os mocks dos coletores, a idempotência do armazenamento, a validação
  dos eventos, a integração dbt com choque sintético e o dashboard via AppTest.
- `python -m src.pipeline` (coleta real + carga + `dbt build`): **concluído, dbt 52/52 OK**. A
  segunda coleta só baixou o que faltava (BCB: 0 linhas novas; Yahoo: 2 diárias e 4 horárias;
  GDELT: 4) e só os Parquet de outubro mudaram.
- Docker: `docker compose --profile pipeline run --rm pipeline python -m src.pipeline --sem-coleta`
  OK (52/52); `docker compose up app` respondeu em http://localhost:8501 e as abas renderizaram
  (conferidas por captura de tela).
- Dados no DuckDB: BCB 700 linhas, Yahoo 2.060 diárias + 27.129 horárias, GDELT 148 dias,
  2 eventos.

## Resultado principal (1º turno, dia 0 = 05/10/2026)

- **Ibovespa:** CAR de +10,5% em [-1,+3] (p < 0,0001); +9,96% na janela horária (p < 0,0001).
- **Real:** retorno anormal de −2,8% (Yahoo) / −2,7% (BCB) contra a média de MXN/CLP/COP/ZAR
  (p ≈ 0,04), ou seja, o real se valorizou além dos pares.
- **Ações vs. Ibovespa (modelo de mercado):** Vale −11,7% (***), Banco do Brasil −7,4% (***),
  Petrobras +7,4% (*), Itaú ≈ 0 (n.s.).
- **2º turno (25/10):** `aguardando_dados` até a coleta trazer os pregões de 26/10 em diante.

Tudo descritivo: um único evento com janela completa, sem pretensão causal.

## O que falhou ou ficou limitado

- **GDELT instável:** a API bloqueou várias requisições por limite de taxa ("Please limit
  requests to one every 5 seconds"), mesmo com 6 s de intervalo. A coleta precisou de várias
  rodadas e tem recuo exponencial. Os dados vieram **ralos e com lacunas** (dias ausentes; total
  monitorado oscilando de ~4 mil a ~170 mil artigos/dia), e a API só pesquisa ~3 meses (desde
  26/07/2026, não desde 01/01). Por isso o GDELT ficou só descritivo.
- **`"Lula"` entre aspas é recusado pelo GDELT** ("phrase is too short"). Regra única adotada:
  nome com várias palavras vai entre aspas; nome de uma palavra, sem aspas. Mesmo assim, os
  níveis de volume não são comparáveis entre os dois nomes.
- **Data das moedas no Yahoo diário vinha deslocada em 1 dia** (descoberto na carga real):
  corrigido no staging e validado contra o BCB e contra as barras de 1h (ver `DECISOES.md`).
- **BCB/SGS intermitente** (timeout e HTML em vez de JSON numa das rodadas): resolvido com
  retentativas.
- **Site do TSE bloqueia acesso automatizado (HTTP 403):** a fonte dos eventos foi conferida
  por buscas que citam a página do TSE e a Res. 23.751/2026. **Vale você abrir os links do
  `eventos.csv` no navegador e confirmar.**
- **Python 3.12 não estava instalado na máquina:** usei 3.13 no venv local; o 3.12 roda no
  Docker (e no CI).
- Não consegui verificar no GitHub real: **o repositório não foi publicado** (não há remoto e
  eu não publico nada sem a sua confirmação), então os workflows só foram validados
  sintaticamente e pelas mesmas etapas rodadas localmente.

## Decisões principais (detalhes em `DECISOES.md`)

- Parquet particionado por mês (só o arquivo do mês corrente muda a cada hora).
- Eventos às 17h (hora oficial de fim da votação e início da divulgação); 2º turno incluído
  mesmo sendo futuro; nenhum debate/pesquisa/declaração (sem fonte verificada com hora exata).
- Janelas contadas em pregões/barras do próprio ativo; corte às 17h para o dia 0.
- Ibovespa com modelo de média constante (não há índice mais amplo na lista).
- Dólar do BCB analisado como segunda fonte do real (robustez).
- Exclusão, na estimação, de observações que caem na janela de outro evento.
- p-valor também para janelas parciais com ≥ metade das observações (status visível).
- Cores neutras (laranja/água) para os candidatos, atribuídas em ordem alfabética.

## Próximos passos para você

1. **Publicar no GitHub** (README → "Subindo no GitHub"): `gh repo create eleicoes-mercado
   --public --source . --push`, depois ativar "Read and write permissions" em
   Settings → Actions e rodar "Coleta de dados" manualmente uma vez.
2. **Depois de 26/10**, abrir o dashboard: o 2º turno sai de `aguardando_dados` sozinho
   (no CI ou com `python -m src.pipeline`). Atualizar a seção "Resultados" do README.
3. **Conferir os links do TSE** em `data/eventos.csv`. Se quiser, acrescentar eventos com hora
   verificável (debates, divulgação de pesquisas registradas no TSE), sempre com a fonte.
4. **Robustez estatística:** testes não paramétricos (sinal/posto, Corrado), correção de
   Patell/BMP para variância de eventos, erro-padrão com correção do erro de estimação e um
   índice global (ex.: EEM ou MSCI EM) como mercado para o Ibovespa.
5. **GDELT:** testar `sourcelang:portuguese` no lugar de `sourcecountry:brazil` (volumes
   muito baixos) ou migrar para o GDELT GKG/BigQuery para ter histórico desde janeiro.
6. Opcional: rodar o dashboard no Streamlit Community Cloud lendo o DuckDB gerado no CI.
