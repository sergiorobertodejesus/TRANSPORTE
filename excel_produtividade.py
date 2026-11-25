"""Exportacao Excel da produtividade operacional."""

from datetime import date, datetime
from periodo_operacional import FUSO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.utils import get_column_letter


AZUL = "153B50"
VERDE = "176B3A"
MOEDA = '"R$" #,##0.00'


def formatar(aba, moedas=(), decimais=(), total=False):
    aba.sheet_view.showGridLines = False
    aba.freeze_panes = "A2"

    for linha in aba.iter_rows():
        for celula in linha:
            celula.alignment = Alignment(
                vertical="center"
            )

            if celula.row == 1 or (
                total and celula.row == aba.max_row
            ):
                celula.fill = PatternFill(
                    "solid", fgColor=AZUL
                )
                celula.font = Font(
                    color="FFFFFF", bold=True
                )

            elif celula.row % 2 == 0:
                celula.fill = PatternFill(
                    "solid", fgColor="EDF3F7"
                )

            if celula.row > 1:
                if celula.column in moedas:
                    celula.number_format = MOEDA

                elif celula.column in decimais:
                    celula.number_format = "0.00"

        aba.row_dimensions[linha[0].row].height = 23

    for coluna in aba.columns:
        largura = max(
            len(str(c.value or ""))
            for c in coluna
        )

        aba.column_dimensions[
            get_column_letter(coluna[0].column)
        ].width = min(42, max(17, largura + 4))


def grafico(aba, origem, coluna, titulo, ancora, cor):
    ultima = origem.max_row - 1

    if ultima < 2:
        return

    if not any(
        origem.cell(linha, coluna).value is not None
        for linha in range(2, ultima + 1)
    ):
        return

    chart = BarChart()
    chart.type = "bar"
    chart.title = titulo
    chart.width = 23
    chart.height = max(7, ultima * 0.65 + 3)
    chart.legend = None
    chart.y_axis.scaling.min = 0
    chart.dataLabels = None

    chart.add_data(
        Reference(
            origem,
            min_col=coluna,
            min_row=1,
            max_row=ultima
        ),
        titles_from_data=True
    )

    chart.set_categories(
        Reference(
            origem,
            min_col=1,
            min_row=2,
            max_row=ultima
        )
    )

    chart.series[0].graphicalProperties.solidFill = cor
    chart.series[0].graphicalProperties.line.noFill = True

    chart.dataLabels = DataLabelList(
        showVal=True,
        showLegendKey=False,
        showCatName=False,
        showSerName=False,
        showPercent=False,
        numFmt=MOEDA
    )

    aba.add_chart(chart, ancora)


def horario_brasilia(valor):
    try:
        horario = datetime.fromisoformat(valor)

        if horario.tzinfo is None:
            return valor

        return horario.astimezone(FUSO).replace(tzinfo=None)

    except (TypeError, ValueError, OverflowError):
        return valor


def indicadores(total):
    return [
        total["jornadas"],
        total["bruto"],
        total["km"],
        total["horas"],
        total["reais_km"],
        total["reais_hora"],
        total["km_invalidos"],
        total["horarios_invalidos"],
    ]


def gerar_excel_produtividade(resultado, destino):
    wb = Workbook()

    resumo = wb.active
    resumo.title = "Resumo"

    geral = resultado["geral"]

    resumo.append(["ER TRANSPORTE", "PRODUTIVIDADE"])
    resumo.append([
        "Data de referência",
        date.fromisoformat(resultado["data"])
    ])
    resumo.append(["Jornadas encerradas", geral["jornadas"]])
    resumo.append(["Faturamento bruto", geral["bruto"]])
    resumo.append(["Quilometragem total", geral["km"]])
    resumo.append(["Horas de jornada", geral["horas"]])
    resumo.append(["Faturamento por KM", geral["reais_km"]])
    resumo.append(["Faturamento por hora", geral["reais_hora"]])
    resumo.append(["KM inválidos", geral["km_invalidos"]])
    resumo.append(["Horários inválidos", geral["horarios_invalidos"]])

    formatar(resumo)

    resumo["B2"].number_format = "DD/MM/YYYY"
    resumo["B6"].number_format = "0.00"

    for endereco in ("B4", "B7", "B8"):
        resumo[endereco].number_format = MOEDA
        resumo[endereco].font = Font(
            bold=True, color=VERDE, size=14
        )

    resumo.column_dimensions["A"].width = 32
    resumo.column_dimensions["B"].width = 25

    observacoes = [
        "CRITÉRIOS DE PRODUTIVIDADE",
        "Fechamento: 07h às 07h - Brasília.",
        "Horas incluem pausas e recargas.",
        "Indicadores usam denominadores válidos.",
        "Campos vazios indicam taxa indisponível.",
        "KM zero não entra no calculo de R$/km.",
    ]

    for numero, texto in enumerate(observacoes, 13):
        resumo.merge_cells(
            start_row=numero, start_column=1,
            end_row=numero, end_column=2
        )
        resumo.cell(numero, 1, texto)
        resumo.row_dimensions[numero].height = 25

    cabecalho = [
        "Jornadas", "Bruto", "KM", "Horas",
        "R$/km", "R$/hora",
        "KM inválidos", "Horários inválidos"
    ]

    motoristas = wb.create_sheet("Motoristas")
    motoristas.append(["Motorista"] + cabecalho)

    for chave, total in sorted(
        resultado["motoristas"].items(),
        key=lambda item: item[0][1]
    ):
        motoristas.append(
            [chave[1]] + indicadores(total)
        )

    motoristas.append(["TOTAL"] + indicadores(geral))

    formatar(
        motoristas,
        moedas=(3, 6, 7),
        decimais=(5,),
        total=True
    )

    veiculos = wb.create_sheet("Veículos")
    veiculos.append(["Veículo", "Placa"] + cabecalho)

    for chave, total in sorted(
        resultado["veiculos"].items(),
        key=lambda item: item[0][1]
    ):
        veiculos.append(
            [chave[1], chave[2]] + indicadores(total)
        )

    veiculos.append(
        ["TOTAL", None] + indicadores(geral)
    )

    formatar(
        veiculos,
        moedas=(4, 7, 8),
        decimais=(6,),
        total=True
    )

    jornadas = wb.create_sheet("Jornadas")

    jornadas.append([
        "ID", "Motorista", "Veículo", "Placa",
        "Início (Brasília)", "Fim (Brasília)",
        "KM inicial", "KM final", "KM rodados",
        "Horas", "Bruto", "R$/km", "R$/hora",
        "Conferência"
    ])

    for j in resultado["jornadas"]:
        alertas = []

        if j["km"] is None:
            alertas.append("KM inválido")
        elif j["km"] == 0:
            alertas.append("KM zero")

        if j["segundos"] is None:
            alertas.append("Horário inválido")

        jornadas.append([
            j["id"], j["motorista"], j["veiculo"],
            j["placa"],
            horario_brasilia(j["data_inicio"]),
            horario_brasilia(j["data_fim"]),
            j["km_inicial"], j["km_final"], j["km"],
            j["horas"], j["bruto"], j["reais_km"],
            j["reais_hora"],
            "; ".join(alertas) or "OK"
        ])

    formatar(
        jornadas,
        moedas=(11, 12, 13),
        decimais=(10,)
    )

    jornadas.auto_filter.ref = jornadas.dimensions

    for linha in range(2, jornadas.max_row + 1):
        for coluna in (5, 6):
            jornadas.cell(linha, coluna).number_format = (
                "DD/MM/YYYY HH:MM"
            )

        conferencia = jornadas.cell(linha, 14)

        if conferencia.value != "OK":
            conferencia.font = Font(
                color="9C0006", bold=True
            )
            conferencia.fill = PatternFill(
                "solid", fgColor="FFC7CE"
            )

    jornadas.column_dimensions["A"].width = 8
    jornadas.column_dimensions["E"].width = 23
    jornadas.column_dimensions["F"].width = 23

    jornadas.freeze_panes = "B2"

    grafico(
        resumo, motoristas, 7,
        "Faturamento por hora - Motoristas",
        "D2", AZUL
    )

    grafico(
        resumo, veiculos, 7,
        "Faturamento por KM - Veículos",
        f"D{max(15, 5 + motoristas.max_row * 2)}", VERDE
    )

    grafico(
        motoristas, motoristas, 6,
        "Faturamento por KM - Motoristas",
        f"A{motoristas.max_row + 3}", AZUL
    )

    grafico(
        veiculos, veiculos, 8,
        "Faturamento por hora - Veículos",
        f"A{veiculos.max_row + 3}", VERDE
    )

    wb.save(destino)
    wb.close()
