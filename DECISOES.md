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
