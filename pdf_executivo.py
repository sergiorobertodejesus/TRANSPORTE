from datetime import date, timedelta
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, PageBreak
)
from reportlab.graphics.shapes import Drawing, Rect, String


AZUL = colors.HexColor("#153B50")
VERDE = colors.HexColor("#176B3A")
CINZA = colors.HexColor("#EDF3F7")
LARANJA = colors.HexColor("#B45309")
TEXTO = colors.HexColor("#334155")

LARGURA = 400
ALTURA = 760
AREA = 364


def numero(valor, casas=2):
    if valor is None:
        return "-"
    texto = f"{valor:,.{casas}f}"
    return texto.translate(str.maketrans(",.", ".,"))


def moeda(valor):
    if valor is None:
        return "-"
    return "R$ " + numero(valor)


def paragrafo(texto, tamanho=11, cor=TEXTO,
              negrito=False, alinhamento=0):
    estilo = ParagraphStyle(
        "Executivo",
        fontName="Helvetica-Bold" if negrito else "Helvetica",
        fontSize=tamanho,
        leading=tamanho * 1.25,
        textColor=cor,
        alignment=alinhamento
    )
    return Paragraph(escape(str(texto)), estilo)


def titulo(texto):
    return paragrafo(texto, 15, AZUL, True)


def tabela(linhas, larguras, cabecalho=True):
    t = Table(linhas, colWidths=larguras, repeatRows=1 if cabecalho else 0)

    comandos = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]

    if cabecalho:
        comandos += [
            ("BACKGROUND", (0, 0), (-1, 0), AZUL),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [CINZA, colors.white]),
        ]
    else:
        comandos.append(
            ("BACKGROUND", (0, 0), (-1, -1), CINZA)
        )

    t.setStyle(TableStyle(comandos))
    return t


def indicador(rotulo, valor, cor=AZUL):
    return [
        paragrafo(rotulo, 10),
        Spacer(1, 4),
        paragrafo(valor, 19, cor, True)
    ]


def cabecalho(secao, referencia):
    return [
        paragrafo("ER TRANSPORTE", 23, AZUL, True),
        paragrafo(secao, 15, VERDE, True),
        Spacer(1, 7),
        paragrafo(referencia, 10),
        Spacer(1, 10)
    ]


def grafico_veiculos(veiculos):
    itens = sorted(
        veiculos.items(),
        key=lambda item: item[0][1]
    )

    altura = max(40, len(itens) * 35 + 22)
    desenho = Drawing(AREA, altura)

    maximo = max(
        [abs(float(t["bruto"])) for _, t in itens]
        + [abs(float(t["liquido"])) for _, t in itens]
        + [1]
    )

    desenho.add(Rect(0, altura-10, 9, 9,
                     fillColor=AZUL, strokeColor=None))
    desenho.add(String(14, altura-9, "Bruto",
                       fontSize=9, fillColor=TEXTO))

    desenho.add(Rect(80, altura-10, 9, 9,
                     fillColor=VERDE, strokeColor=None))
    desenho.add(String(94, altura-9, "Líquido",
                       fontSize=9, fillColor=TEXTO))

    for i, (chave, total) in enumerate(itens):
        y = altura - 30 - i * 35

        desenho.add(String(
            0, y, str(chave[1]),
            fontName="Helvetica-Bold",
            fontSize=11, fillColor=AZUL
        ))

        for campo, cor, posicao in (
            ("bruto", AZUL, y-11),
            ("liquido", VERDE, y-22)
        ):
            valor = float(total[campo])

            if valor > 0:
                desenho.add(Rect(
                    0, posicao,
                    valor / maximo * 245, 7,
                    fillColor=cor, strokeColor=None
                ))

            desenho.add(String(
                AREA, posicao+1, moeda(total[campo]),
                textAnchor="end",
                fontSize=10,
                fillColor=LARANJA if valor < 0 else TEXTO
            ))

    return desenho


def rodape(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(CINZA)
    canvas.line(18, 32, LARGURA-18, 32)
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(TEXTO)
    canvas.drawString(18, 18, "ER Transporte | Uso interno")
    canvas.drawRightString(
        LARGURA-18, 18, f"Página {doc.page}"
    )
    canvas.restoreState()


def gerar_pdf_executivo(financeiro, produtividade, destino):
    if financeiro["data"] != produtividade["data"]:
        raise ValueError("Períodos dos relatórios divergentes.")

    f = financeiro["geral"]
    p = produtividade["geral"]

    if f["bruto"] != p["bruto"] or f["jornadas"] != p["jornadas"]:
        raise ValueError("Totais dos relatórios divergentes.")

    dia = date.fromisoformat(financeiro["data"])
    seguinte = dia + timedelta(days=1)

    referencia = (
        f"{dia:%d/%m/%Y} às 07h até "
        f"{seguinte:%d/%m/%Y} às 07h"
    )

    doc = SimpleDocTemplate(
        str(destino),
        pagesize=(LARGURA, ALTURA),
        leftMargin=18,
        rightMargin=18,
        topMargin=18,
        bottomMargin=43,
        title="ER Transporte - Relatório Executivo",
        author="ER Transporte"
    )

    historia = cabecalho("Relatório Executivo Diário", referencia)

    # PÁGINA 1 - VISÃO EXECUTIVA

    historia.append(tabela([
        [
            indicador("Faturamento bruto", moeda(f["bruto"])),
            indicador("Líquido operacional", moeda(f["liquido"]), VERDE)
        ],
        [
            indicador("Despesas totais", moeda(f["despesas"]), LARANJA),
            indicador("Jornadas encerradas", str(f["jornadas"]))
        ]
    ], [AREA/2, AREA/2], False))

    historia += [
        Spacer(1, 10),
        titulo("Resultado por veículo"),
        Spacer(1, 8),
        grafico_veiculos(financeiro["veiculos"]),
        Spacer(1, 10),
        titulo("Despesas registradas"),
        Spacer(1, 7),
        tabela([
            [paragrafo("Recargas"), paragrafo(moeda(f["recarga"]), 12, AZUL, True, 2)],
            [paragrafo("Combustível"), paragrafo(moeda(f["combustivel"]), 12, AZUL, True, 2)],
            [paragrafo("Outras despesas"), paragrafo(moeda(f["outras_despesas"]), 12, AZUL, True, 2)]
        ], [AREA/2, AREA/2], False),
        Spacer(1, 8),
        titulo("Produtividade geral"),
        Spacer(1, 7),
        tabela([
            [
                indicador("Quilometragem", numero(p["km"], 0) + " km"),
                indicador("Horas de jornada", numero(p["horas"], 1) + " h")
            ],
            [
                indicador("Faturamento por km", moeda(p["reais_km"]), VERDE),
                indicador("Faturamento por hora", moeda(p["reais_hora"]), VERDE)
            ]
        ], [AREA/2, AREA/2], False),
        Spacer(1, 8),
        paragrafo(
            "Líquido operacional = bruto menos despesas registradas. "
            "Não representa o lucro final da empresa.", 9
        )
    ]

    # PÁGINA 2 - MOTORISTAS

    historia.append(PageBreak())
    historia += cabecalho("Desempenho dos motoristas", referencia)

    linhas = [[
        paragrafo("Motorista", 10, colors.white, True),
        paragrafo("Bruto / Líquido", 10, colors.white, True),
        paragrafo("Produtividade", 10, colors.white, True)
    ]]

    for chave, total in sorted(
        financeiro["motoristas"].items(),
        key=lambda item: item[0][1]
    ):
        prod = produtividade["motoristas"][chave]

        linhas.append([
            [
                paragrafo(chave[1], 11, AZUL, True),
                paragrafo(f'{total["jornadas"]} jornada(s)', 9)
            ],
            [
                paragrafo(moeda(total["bruto"]), 11, AZUL, True),
                paragrafo(moeda(total["liquido"]), 11, VERDE, True)
            ],
            [
                paragrafo(numero(prod["km"], 0) + " km", 10),
                paragrafo(moeda(prod["reais_km"]) + "/km", 10),
                paragrafo(moeda(prod["reais_hora"]) + "/h", 10)
            ]
        ])

    historia += [
        tabela(linhas, [120, 122, 122]),
        Spacer(1, 8),
        paragrafo(
            "As horas de jornada incluem pausas e recargas. "
            "Taxas indisponíveis são representadas por um traço.", 9
        )
    ]

    # PÁGINA 3 - FROTA

    historia.append(PageBreak())
    historia += cabecalho("Desempenho da frota", referencia)

    for chave, total in sorted(
        financeiro["veiculos"].items(),
        key=lambda item: item[0][1]
    ):
        prod = produtividade["veiculos"][chave]

        historia += [
            paragrafo(chave[1], 14, AZUL, True),
            Spacer(1, 4),
            tabela([
                [
                    paragrafo("Bruto: " + moeda(total["bruto"]), 11, AZUL, True),
                    paragrafo("Líquido: " + moeda(total["liquido"]), 11, VERDE, True)
                ],
                [
                    paragrafo("Recarga: " + moeda(total["recarga"]), 10),
                    paragrafo("Combustível: " + moeda(total["combustivel"]), 10)
                ],
                [
                    paragrafo(numero(prod["km"], 0) + " km rodados", 10),
                    paragrafo(moeda(prod["reais_km"]) + "/km", 10)
                ]
            ], [AREA/2, AREA/2], False),
            Spacer(1, 10)
        ]

    historia.append(paragrafo(
        f'Conferência: {p["km_invalidos"]} registro(s) com KM inválido '
        f'e {p["horarios_invalidos"]} com horário inválido.', 9
    ))

    doc.build(
        historia,
        onFirstPage=rodape,
        onLaterPages=rodape
    )
