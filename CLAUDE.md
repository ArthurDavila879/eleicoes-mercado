# CLAUDE.md — guia do repositório

Estudo de evento sobre a reação do mercado brasileiro a eventos das eleições de 2026.
O projeto é **neutro**: mede a reação do mercado, não avalia candidatos; a mesma
metodologia (e a mesma consulta-base no GDELT) vale para todos.

## Convenções
- Código, comentários, nomes de tabelas/colunas e textos em **português**.
- Python 3.12 (Docker/CI). DuckDB como banco analítico, dbt-duckdb para as transformações.
- Horários: armazenados em **UTC sem fuso** (`data_hora_utc`); o fuso de referência do
  estudo é `America/Sao_Paulo` (UTC−3, sem horário de verão desde 2019).
- Não inventar eventos em `data/eventos.csv`: só datas certas e verificáveis, com fonte.
- Decisões de projeto ficam registradas em `DECISOES.md`.

## Estrutura
- `src/ingestao/` — coletores (BCB/SGS, yfinance, GDELT, Binance), armazenamento Parquet
  particionado por mês em `data/bruto/` e carga no DuckDB (`data/eleicoes.duckdb`).
- `src/eventos/` — validação de `data/eventos.csv`.
- `src/estatistica/` — estudo de evento em Python (Patell, BMP, Corrado, placebo, sensibilidade),
  chamado pelos modelos Python de robustez do dbt; deve reproduzir os modelos SQL.
- `src/pipeline.py` — coleta → validação → carga → `dbt build`.
- `dbt/` — modelos: `staging` → `intermediario` (log-retornos, janelas) → `marts`
  (retornos anormais, CAR e significância; robustez em `fct_testes_robustez`,
  `fct_placebo_*` e `fct_sensibilidade_janelas`; volatilidade/volume em `fct_atividade_anormal`).
- `app.py` — dashboard Streamlit (porta 8501); reconstrói o DuckDB a partir dos Parquet se
  faltar ou estiver desatualizado (`src/banco.py`), como no Streamlit Community Cloud.
- `tests/` — pytest com respostas mockadas (sem rede).

## Comandos
```bash
pip install -r requirements-dev.txt
pytest -q                                   # testes (sem rede)
python -m src.ingestao                      # coleta incremental (rede)
python -m src.pipeline                      # coleta + carga + dbt build
python -m src.pipeline --sem-coleta         # só carga + dbt build com os Parquet existentes
python -m src.pipeline --sem-coleta --verificar-atualizacao  # + testes de atualização (tag atualizacao)
dbt build --project-dir dbt --profiles-dir dbt --exclude tag:atualizacao
streamlit run app.py
docker compose --profile pipeline run --rm pipeline && docker compose up app
```
