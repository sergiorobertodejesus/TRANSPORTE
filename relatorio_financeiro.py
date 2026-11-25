"""Consolidação financeira diária da ER Transporte."""

from collections import defaultdict
from datetime import date
from consulta_jornadas import consultar_jornadas
from decimal import Decimal


def monetario(valor):
    return Decimal(str(valor or 0)).quantize(Decimal("0.01"))


def novo_total():
    return {
        "jornadas": 0,
        "bruto": Decimal("0.00"),
        "despesas": Decimal("0.00"),
        "liquido": Decimal("0.00"),
        "recarga": Decimal("0.00"),
        "combustivel": Decimal("0.00"),
        "outras_despesas": Decimal("0.00"),
    }


def acumular(destino, origem):
    for campo in destino:
        destino[campo] += origem[campo]


def consolidar_financeiro(db, dia):
    dia = date.fromisoformat(dia).isoformat()

    jornadas = consultar_jornadas(db, dia)

    geral = novo_total()
    motoristas = defaultdict(novo_total)
    veiculos = defaultdict(novo_total)

    for jornada in jornadas:
        valores = novo_total()
        valores["jornadas"] = 1

        for campo in (
            "bruto", "despesas", "recarga", "combustivel"
        ):
            valores[campo] = monetario(jornada[campo])

        valores["liquido"] = (
            valores["bruto"] - valores["despesas"]
        )

        valores["outras_despesas"] = (
            valores["despesas"]
            - valores["recarga"]
            - valores["combustivel"]
        )

        motorista = (
            jornada["motorista_id"],
            jornada["motorista"],
        )

        veiculo = (
            jornada["veiculo_id"],
            jornada["veiculo"],
            jornada["placa"],
        )

        acumular(geral, valores)
        acumular(motoristas[motorista], valores)
        acumular(veiculos[veiculo], valores)

    return {
        "data": dia,
        "geral": geral,
        "motoristas": dict(motoristas),
        "veiculos": dict(veiculos),
    }
