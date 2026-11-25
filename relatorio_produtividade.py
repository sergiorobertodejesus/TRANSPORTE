"""Consolidacao da produtividade operacional."""

from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal

from consulta_jornadas import consultar_jornadas
from relatorio_financeiro import monetario


def calcular_distancia(inicial, final):
    if inicial is None or final is None:
        return None

    if inicial < 0 or final < inicial:
        return None

    return final - inicial


def calcular_segundos(inicio, fim):
    try:
        inicio = datetime.fromisoformat(inicio)
        fim = datetime.fromisoformat(fim)

        if inicio.tzinfo is None or fim.tzinfo is None:
            return None

        segundos = (
            fim.astimezone(timezone.utc)
            - inicio.astimezone(timezone.utc)
        ).total_seconds()

        if segundos <= 0:
            return None

        return int(segundos)

    except (TypeError, ValueError, OverflowError):
        return None


def dividir(valor, divisor):
    if divisor is None or divisor <= 0:
        return None

    return monetario(valor / Decimal(str(divisor)))


def novo_total():
    return {
        "jornadas": 0,
        "bruto": Decimal("0.00"),
        "km": 0,
        "segundos": 0,
        "bruto_km": Decimal("0.00"),
        "bruto_horas": Decimal("0.00"),
        "km_invalidos": 0,
        "horarios_invalidos": 0,
    }


def acumular(total, jornada):
    total["jornadas"] += 1
    total["bruto"] += jornada["bruto"]

    km = jornada["km"]
    segundos = jornada["segundos"]

    if km is None:
        total["km_invalidos"] += 1
    else:
        total["km"] += km

        if km > 0:
            total["bruto_km"] += jornada["bruto"]

    if segundos is None:
        total["horarios_invalidos"] += 1
    else:
        total["segundos"] += segundos
        total["bruto_horas"] += jornada["bruto"]


def finalizar(total):
    total["horas"] = (
        Decimal(total["segundos"]) / Decimal(3600)
    )

    total["reais_km"] = dividir(
        total["bruto_km"], total["km"]
    )

    total["reais_hora"] = dividir(
        total["bruto_horas"] * Decimal(3600),
        total["segundos"]
    )

    return total


def consolidar_produtividade(db, dia):
    dia = date.fromisoformat(dia).isoformat()

    geral = novo_total()
    motoristas = defaultdict(novo_total)
    veiculos = defaultdict(novo_total)
    detalhes = []

    for registro in consultar_jornadas(db, dia):
        jornada = dict(registro)

        jornada["bruto"] = monetario(registro["bruto"])

        jornada["km"] = calcular_distancia(
            registro["km_inicial"],
            registro["km_final"]
        )

        jornada["segundos"] = calcular_segundos(
            registro["data_inicio"],
            registro["data_fim"]
        )

        segundos = jornada["segundos"]

        jornada["horas"] = (
            Decimal(segundos) / Decimal(3600)
            if segundos is not None else None
        )

        jornada["reais_km"] = dividir(
            jornada["bruto"], jornada["km"]
        )

        jornada["reais_hora"] = dividir(
            jornada["bruto"] * Decimal(3600),
            segundos
        )

        motorista = (
            registro["motorista_id"],
            registro["motorista"]
        )

        veiculo = (
            registro["veiculo_id"],
            registro["veiculo"],
            registro["placa"]
        )

        acumular(geral, jornada)
        acumular(motoristas[motorista], jornada)
        acumular(veiculos[veiculo], jornada)

        detalhes.append(jornada)

    return {
        "data": dia,
        "geral": finalizar(geral),
        "motoristas": {
            chave: finalizar(total)
            for chave, total in motoristas.items()
        },
        "veiculos": {
            chave: finalizar(total)
            for chave, total in veiculos.items()
        },
        "jornadas": detalhes,
    }
