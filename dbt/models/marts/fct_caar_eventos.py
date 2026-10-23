"""Análise agregada entre eventos (diária): CAAR, t agregado, t transversal e qui-quadrado
sem direção, por ativo e grupo de eventos (todos, 1º turnos, 2º turnos). Ver
src/estatistica/agregado.py."""

from src.estatistica import agregado


def model(dbt, session):
    dbt.config(materialized="table")
    return agregado.caar(dbt.ref("resultados_eventos").df())
