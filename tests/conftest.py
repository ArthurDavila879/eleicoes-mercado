"""Utilitários de teste: sessão HTTP falsa (sem rede) e diretórios temporários."""

from __future__ import annotations

import json

import pytest


class RespostaFalsa:
    def __init__(self, status_code: int = 200, corpo=None, texto: str | None = None):
        self.status_code = status_code
        self._corpo = corpo
        self.text = texto if texto is not None else json.dumps(corpo)

    def json(self):
        return self._corpo if self._corpo is not None else json.loads(self.text)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class SessaoFalsa:
    """Imita ``requests.Session``: devolve respostas de uma função e registra chamadas."""

    def __init__(self, responder):
        self.responder = responder
        self.chamadas: list[tuple[str, dict]] = []

    def get(self, url, params=None, **_):
        self.chamadas.append((url, dict(params or {})))
        return self.responder(url, params or {})


@pytest.fixture
def dir_bruto(tmp_path):
    caminho = tmp_path / "bruto"
    caminho.mkdir()
    return caminho


@pytest.fixture
def sem_espera(monkeypatch):
    """Elimina os ``time.sleep`` dos coletores para os testes rodarem rápido.

    Não é automático: anular o sleep globalmente trava o executor do Streamlit (AppTest).
    """
    import time

    monkeypatch.setattr(time, "sleep", lambda *_: None)
