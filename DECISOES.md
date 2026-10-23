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
- **GDELT — limite de requisições:** 6 s entre chamadas e recuo exponencial. Se o tom falhar
  mas o volume vier, o volume é salvo e o tom já existente é preservado.
