import duckdb
import pandas as pd

from src.ingestao import armazenamento, carga


def test_carga_cria_tabelas_mesmo_sem_dados(tmp_path, dir_bruto):
    db = tmp_path / "t.duckdb"
    contagens = carga.carregar(db, dir_bruto, tmp_path / "nao_existe.csv")
    assert contagens == {"bcb_sgs": 0, "yahoo_diario": 0, "yahoo_horario": 0, "binance_horario": 0,
                         "gdelt_diario": 0, "eventos": 0}


def test_carga_le_parquet_e_eventos_e_e_idempotente(tmp_path, dir_bruto):
    df = pd.DataFrame({"serie_codigo": [1, 1], "serie_nome": ["dolar_venda"] * 2,
                       "data": pd.to_datetime(["2026-01-30", "2026-02-02"]), "valor": [5.0, 5.1]})
    armazenamento.salvar_incremental(df, "bcb_sgs", ["serie_nome", "data"], "data", dir_bruto)
    eventos = tmp_path / "eventos.csv"
    eventos.write_text("data_hora,tipo,descricao,fonte_url\n"
                       "2026-10-04T17:00:00-03:00,resultado,Fim,https://a.b/c\n", encoding="utf-8")
    db = tmp_path / "t.duckdb"
    for _ in range(2):
        contagens = carga.carregar(db, dir_bruto, eventos)
    assert contagens["bcb_sgs"] == 2 and contagens["eventos"] == 1
    con = duckdb.connect(str(db), read_only=True)
    assert con.execute("select data_hora_utc from bruto.eventos").fetchall()[0][0] == pd.Timestamp("2026-10-04 20:00")
    con.close()
