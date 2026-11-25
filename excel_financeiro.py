"""Apresentação do relatório financeiro da ER Transporte."""

from openpyxl import Workbook
from datetime import date
from openpyxl.chart.label import DataLabelList
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.chart import BarChart, PieChart, Reference
from openpyxl.utils import get_column_letter


AZUL = "153B50"
VERDE = "176B3A"
MOEDA = '"R$" #,##0.00'


def formatar_tabela(aba, colunas_moeda):
    aba.freeze_panes = "B2"
    aba.sheet_view.showGridLines = False

    for celula in aba[1]:
        celula.font = Font(bold=True, color="FFFFFF")
        celula.fill = PatternFill("solid", fgColor=AZUL)
        celula.alignment = Alignment(horizontal="center")

    for linha in aba.iter_rows(min_row=2):
        for celula in linha:
            if celula.column in colunas_moeda:
                celula.number_format = MOEDA

            if celula.row % 2 == 0:
                celula.fill = PatternFill(
                    "solid", fgColor="EDF3F7"
                )

    for coluna in aba.columns:
        largura = max(
            len(str(c.value or "")) for c in coluna
        )
        letra = get_column_letter(coluna[0].column)
        aba.column_dimensions[letra].width = max(
            18, min(largura + 5, 40)
        )

    for celula in aba[aba.max_row]:
        celula.font = Font(bold=True, color="FFFFFF")
        celula.fill = PatternFill("solid", fgColor=AZUL)


def gerar_excel_financeiro(resultado, destino):
    wb = Workbook()
    resumo = wb.active
    resumo.title = "Resumo"

    geral = resultado["geral"]

    resumo.append(["ER TRANSPORTE", "RELATÓRIO FINANCEIRO"])
    resumo.append(["Data de referência", date.fromisoformat(resultado["data"])])
    resumo.append(["Jornadas encerradas", geral["jornadas"]])
    resumo.append(["Faturamento bruto", geral["bruto"]])
    resumo.append(["Despesas totais", geral["despesas"]])
    resumo.append(["Líquido operacional", geral["liquido"]])
    resumo.append([])
    resumo.append(["Categoria", "Valor"])
    resumo.append(["Recargas", geral["recarga"]])
    resumo.append(["Combustível", geral["combustivel"]])
    resumo.append(["Outras despesas", geral["outras_despesas"]])
    resumo.append(["Total", geral["despesas"]])

    formatar_tabela(resumo, {2})

    resumo["B3"].number_format = "0"
    resumo["B6"].font = Font(
        bold=True, color=VERDE, size=16
    )
    resumo.column_dimensions["A"].width = 30
    resumo.column_dimensions["B"].width = 30

    motoristas = wb.create_sheet("Motoristas")

    motoristas.append([
        "Motorista", "Jornadas",
        "Bruto", "Despesas", "Líquido"
    ])

    for chave, valores in sorted(
        resultado["motoristas"].items(),
        key=lambda item: item[0][1]
    ):
        motoristas.append([
            chave[1],
            valores["jornadas"],
            valores["bruto"],
            valores["despesas"],
            valores["liquido"]
        ])

    motoristas.append([
        "TOTAL", geral["jornadas"],
        geral["bruto"], geral["despesas"],
        geral["liquido"]
    ])

    formatar_tabela(motoristas, {3, 4, 5})

    veiculos = wb.create_sheet("Veículos")

    veiculos.append([
        "Veículo", "Placa", "Jornadas",
        "Bruto", "Despesas", "Líquido"
    ])

    energia = wb.create_sheet("Recargas e combustíveis")

    energia.append([
        "Veículo", "Placa", "Recarga",
        "Combustível", "Total abastecimento"
    ])

    for chave, valores in sorted(
        resultado["veiculos"].items(),
        key=lambda item: item[0][1]
    ):
        veiculos.append([
            chave[1], chave[2], valores["jornadas"],
            valores["bruto"], valores["despesas"],
            valores["liquido"]
        ])

        energia.append([
            chave[1], chave[2],
            valores["recarga"],
            valores["combustivel"],
            valores["recarga"] + valores["combustivel"]
        ])

    veiculos.append([
        "TOTAL", "", geral["jornadas"],
        geral["bruto"], geral["despesas"],
        geral["liquido"]
    ])

    energia.append([
        "TOTAL", "", geral["recarga"],
        geral["combustivel"],
        geral["recarga"] + geral["combustivel"]
    ])

    formatar_tabela(veiculos, {4, 5, 6})
    formatar_tabela(energia, {3, 4, 5})

    if resultado["veiculos"]:
        grafico = BarChart()
        grafico.title = "Bruto e líquido por veículo"
        grafico.y_axis.title = "Valor em R$"
        grafico.style = 10
        grafico.width = 23
        grafico.height = 12

        grafico.add_data(
            Reference(
                veiculos, min_col=4, max_col=4,
                min_row=1, max_row=veiculos.max_row - 1
            ),
            titles_from_data=True
        )

        grafico.add_data(
            Reference(
                veiculos, min_col=6,
                min_row=1, max_row=veiculos.max_row - 1
            ),
            titles_from_data=True
        )

        grafico.set_categories(
            Reference(
                veiculos, min_col=1,
                min_row=2, max_row=veiculos.max_row - 1
            )
        )

        grafico.series[0].graphicalProperties.solidFill = AZUL
        grafico.series[1].graphicalProperties.solidFill = VERDE

        resumo.add_chart(grafico, "D2")

    if geral["despesas"] > 0:
        pizza = PieChart()
        pizza.title = "Distribuição das despesas"
        pizza.width = 18
        pizza.height = 10

        pizza.add_data(
            Reference(resumo, min_col=2, min_row=9, max_row=11)
        )

        pizza.set_categories(
            Reference(resumo, min_col=1, min_row=9, max_row=11)
        )

        resumo.add_chart(pizza, "D26")

    resumo["A15"] = "Critério financeiro"
    resumo["A16"] = "Bruto = Uber + 99 + particulares"
    resumo["A17"] = "Líquido = bruto menos despesas registradas"
    resumo["A18"] = "Fechamento: das 07h às 07h (horário de Brasília)"
    resumo["A19"] = "Líquido operacional não equivale ao lucro final."


    # REFINAMENTO VISUAL

    for aba in wb.worksheets:
        aba.freeze_panes = "A2"
        aba.row_dimensions[1].height = 27

        for linha in range(2, aba.max_row + 1):
            aba.row_dimensions[linha].height = 23

    resumo["B2"].number_format = "DD/MM/YYYY"
    resumo["B4"].font = Font(
        bold=True, color=AZUL, size=14
    )

    for celula in resumo[8]:
        celula.fill = PatternFill("solid", fgColor=AZUL)
        celula.font = Font(bold=True, color="FFFFFF")

    for linha in range(15, 20):
        resumo.merge_cells(
            start_row=linha, start_column=1,
            end_row=linha, end_column=2
        )
        resumo.cell(linha, 1).alignment = Alignment(
            wrap_text=True, vertical="center"
        )
        resumo.row_dimensions[linha].height = 30

    resumo["A15"].font = Font(bold=True, color=AZUL)

    if resultado["veiculos"]:
        grafico.width = 23
        grafico.height = 9

        grafico.dataLabels = DataLabelList(
            showLegendKey=False,
            showCatName=False,
            showSerName=False,
            showPercent=False
        )
        grafico.dataLabels.showVal = True
        grafico.dataLabels.dLblPos = "outEnd"
        grafico.dataLabels.numFmt = MOEDA

    if geral["despesas"] > 0:
        pizza.width = 18
        pizza.height = 7
        pizza.anchor = "D17"

        pizza.dataLabels = DataLabelList(
            showLegendKey=False,
            showCatName=False,
            showSerName=False,
            showPercent=True,
            numFmt="0.0%"
        )
        pizza.dataLabels.showPercent = True
        pizza.dataLabels.showVal = False

    def adicionar_grafico(aba, titulo, colunas, cores):
        if aba.max_row <= 2:
            return

        chart = BarChart()
        chart.title = titulo
        chart.y_axis.title = "Valor em R$"
        chart.width = 24
        chart.height = 11

        for coluna in colunas:
            chart.add_data(
                Reference(
                    aba, min_col=coluna,
                    min_row=1, max_row=aba.max_row - 1
                ),
                titles_from_data=True
            )

        chart.set_categories(
            Reference(
                aba, min_col=1,
                min_row=2, max_row=aba.max_row - 1
            )
        )

        for serie, cor in zip(chart.series, cores):
            serie.graphicalProperties.solidFill = cor

        chart.dataLabels = DataLabelList(
            showLegendKey=False,
            showCatName=False,
            showSerName=False,
            showPercent=False
        )
        chart.dataLabels.showVal = True
        chart.dataLabels.dLblPos = "outEnd"
        chart.dataLabels.numFmt = MOEDA

        aba.add_chart(chart, f"A{aba.max_row + 3}")

    adicionar_grafico(
        motoristas,
        "Bruto e líquido por motorista",
        (3, 5),
        (AZUL, VERDE)
    )

    adicionar_grafico(
        energia,
        "Custo de abastecimento por veículo",
        (3, 4),
        (AZUL, "D97706")
    )

    wb.save(destino)
    wb.close()
