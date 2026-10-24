# Operação: deploy, documentação e coleta automática

> Parte do projeto [eleicoes-mercado](../README.md).

## Deploy do dashboard (Streamlit Community Cloud)

O app não precisa de etapa de build: na inicialização, se o DuckDB não existe ou está
desatualizado em relação aos Parquet versionados (impressão digital dos dados, do projeto dbt e
do código), ele roda carga + `dbt build` (sem coleta) num subprocesso e guarda o resultado; a
verificação se repete a cada 10 minutos e só reconstrói quando algo mudou (`src/banco.py`).

1. Entre em [share.streamlit.io](https://share.streamlit.io) com a conta do GitHub e clique em
   **Create app → Deploy a public app from GitHub**.
2. Repositório `ArthurDavila879/eleicoes-mercado`, branch `main`, arquivo principal `app.py`.
3. Em **Advanced settings**, escolha **Python 3.12**. Não há segredos a configurar.
4. **Deploy.** A primeira abertura instala as dependências (`requirements.txt`) e constrói o
   banco (cerca de 30 s a mais); as seguintes abrem direto.
5. A coleta automática commita dados novos no `main`; o Streamlit Cloud atualiza o app sozinho
   e o banco é reconstruído na próxima verificação.

Para desligar a reconstrução automática (por exemplo, num servidor em que o pipeline roda à
parte), defina `ELEICOES_SEM_CONSTRUCAO=1`.

## Documentação dbt no GitHub Pages

O workflow `.github/workflows/docs.yml` gera o `dbt docs` (modelos, colunas, testes e grafo de
linhagem) como página única e publica no GitHub Pages a cada push que muda `dbt/`, `src/` ou os
eventos (ou manualmente, em **Actions → Documentação dbt → Run workflow**). Para ativar:
**Settings → Pages → Build and deployment → Source: GitHub Actions**. Endereço:
<https://arthurdavila879.github.io/eleicoes-mercado/>.

## Subindo no GitHub (para a coleta automática funcionar)

1. Crie um repositório vazio no GitHub (sem README) e envie o código:
   ```bash
   git remote add origin https://github.com/<seu-usuario>/eleicoes-mercado.git
   git push -u origin main
   ```
   ou, com a CLI: `gh repo create eleicoes-mercado --public --source . --push`.
2. Em **Settings → Actions → General → Workflow permissions**, marque **Read and write
   permissions** (o workflow já declara `permissions: contents: write`, mas algumas contas e
   organizações restringem o padrão).
3. Em **Actions**, habilite os workflows se solicitado e rode **Coleta de dados → Run workflow**
   uma vez para testar (`workflow_dispatch`).
4. A partir daí, `.github/workflows/coleta.yml` roda de hora em hora nos dias úteis durante o
   pregão (13h17–21h17 UTC = 10h17–18h17 em Brasília) e uma vez à noite (01h47 UTC = 22h47),
   e commita os Parquet novos em `data/bruto/`. O `testes.yml` roda pytest e o pipeline
   (carga + dbt build) em todo push.

**Monitoramento da coleta.** Ao fim de cada execução, o workflow constrói o banco e roda os
testes de atualização das fontes (tag `atualizacao` no dbt): falham se o último dado de alguma
série (por ticker, série do BCB ou candidato) tiver mais de **2 dias úteis** de atraso — o GDELT só
gera aviso. Se qualquer passo da coleta falhar, o job `avisar_falha` abre uma issue com o rótulo
`coleta-falhou`, ou comenta na que já estiver aberta (não duplica). Feche a issue quando a coleta
voltar ao normal. Esses testes ficam fora do `dbt build` comum (`src.pipeline` os exclui), para
que dados atrasados não impeçam o dashboard de ser construído; com o dbt direto, use
`dbt build --exclude tag:atualizacao`.

Observações: o GitHub pode atrasar execuções agendadas nos horários de pico e desativa
agendamentos em repositórios públicos depois de 60 dias sem atividade. Se a coleta parar,
reative o workflow em **Actions**. Commits feitos com o `GITHUB_TOKEN` não disparam outros
workflows, então a coleta automática não aciona o workflow de testes a cada hora.
