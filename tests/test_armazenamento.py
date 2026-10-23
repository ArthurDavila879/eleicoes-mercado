from datetime import date, datetime

import pandas as pd

from src.ingestao import armazenamento


def _df(valores):
    return pd.DataFrame(
        {"serie": "x", "data": pd.to_datetime(list(valores)), "valor": list(valores.values())}
    )


def test_salvar_cria_particoes_mensais(dir_bruto):
    df = _df({"2026-01-30": 1.0, "2026-02-02": 2.0})
    n = armazenamento.salvar_incremental(df, "fonte", ["serie", "data"], "data", dir_bruto)
    assert n == 2
    assert sorted(p.name for p in (dir_bruto / "fonte").glob("*.parquet")) == [
        "2026-01.parquet", "2026-02.parquet"]


def test_salvar_duas_vezes_e_idempotente(dir_bruto):
    df = _df({"2026-01-30": 1.0, "2026-02-02": 2.0})
    armazenamento.salvar_incremental(df, "fonte", ["serie", "data"], "data", dir_bruto)
    arquivo = dir_bruto / "fonte" / "2026-01.parquet"
    mtime = arquivo.stat().st_mtime_ns
    assert armazenamento.salvar_incremental(df, "fonte", ["serie", "data"], "data", dir_bruto) == 0
    assert arquivo.stat().st_mtime_ns == mtime  # arquivo não foi reescrito
    assert len(armazenamento.ler_fonte("fonte", dir_bruto)) == 2


def test_salvar_atualiza_valor_revisado_sem_duplicar(dir_bruto):
    armazenamento.salvar_incremental(_df({"2026-01-30": 1.0}), "fonte", ["serie", "data"], "data", dir_bruto)
    n = armazenamento.salvar_incremental(
        _df({"2026-01-30": 1.5, "2026-01-31": 3.0}), "fonte", ["serie", "data"], "data", dir_bruto)
    assert n == 2
    lido = armazenamento.ler_fonte("fonte", dir_bruto)
    assert lido["valor"].tolist() == [1.5, 3.0]


def test_horarios_com_fuso_sao_normalizados_para_utc(dir_bruto):
    df = pd.DataFrame({"ticker": ["A"], "t": pd.to_datetime(["2026-10-05 10:00"]).tz_localize("America/Sao_Paulo"), "v": [1.0]})
    armazenamento.salvar_incremental(df, "h", ["ticker", "t"], "t", dir_bruto)
    lido = armazenamento.ler_fonte("h", dir_bruto)
    assert lido["t"].iloc[0] == pd.Timestamp("2026-10-05 13:00")


def test_ultimo_registro_e_inicio_incremental(dir_bruto):
    armazenamento.salvar_incremental(_df({"2026-03-10": 1.0, "2026-03-20": 2.0}), "fonte", ["serie", "data"], "data", dir_bruto)
    ultimos = armazenamento.ultimo_registro("fonte", "serie", "data", dir_bruto)
    assert ultimos == {"x": datetime(2026, 3, 20)}
    assert armazenamento.inicio_incremental(ultimos["x"], 5) == date(2026, 3, 15)
    assert armazenamento.inicio_incremental(None, 5) == date(2026, 1, 1)
    assert armazenamento.inicio_incremental(datetime(2026, 1, 2), 5) == date(2026, 1, 1)
