"""Período operacional da ER Transporte."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


FUSO = ZoneInfo("America/Sao_Paulo")
HORA_FECHAMENTO = 7


def limites_operacionais(dia):
    referencia = date.fromisoformat(dia)

    inicio = datetime.combine(
        referencia,
        time(HORA_FECHAMENTO),
        tzinfo=FUSO
    )

    fim = inicio + timedelta(days=1)

    return inicio, fim
