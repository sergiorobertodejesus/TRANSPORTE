import unittest

from io import BytesIO
from openpyxl import load_workbook

import test_relatorio_produtividade

from relatorio_produtividade import consolidar_produtividade
from excel_produtividade import gerar_excel_produtividade


class TestExcelProdutividade(unittest.TestCase):

    def setUp(self):
        fixture = (
            test_relatorio_produtividade.TestRelatorioProdutividade()
        )

        self.addCleanup(fixture.doCleanups)
        fixture.setUp()

        self.db = fixture.db

    def gerar(self, dia="2026-11-24"):
        resultado = consolidar_produtividade(
            self.db, dia
        )

        arquivo = BytesIO()

        gerar_excel_produtividade(
            resultado, arquivo
        )

        arquivo.seek(0)

        wb = load_workbook(arquivo)
        self.addCleanup(wb.close)

        return wb

    def test_abas(self):
        wb = self.gerar()

        self.assertEqual(
            wb.sheetnames,
            [
                "Resumo",
                "Motoristas",
                "Veículos",
                "Jornadas"
            ]
        )

    def test_indicadores_gerais(self):
        resumo = self.gerar()["Resumo"]

        self.assertEqual(resumo["B3"].value, 3)
        self.assertEqual(resumo["B4"].value, 1250)
        self.assertEqual(resumo["B5"].value, 500)
        self.assertEqual(resumo["B6"].value, 24)
        self.assertEqual(resumo["B7"].value, 2.50)
        self.assertEqual(resumo["B8"].value, 52.08)

    def test_detalhamento_jornadas(self):
        aba = self.gerar()["Jornadas"]

        self.assertEqual(aba.max_row, 4)

        self.assertEqual(
            sum(
                aba.cell(linha, 9).value
                for linha in range(2, 5)
            ),
            500
        )

        self.assertEqual(
            sum(
                aba.cell(linha, 11).value
                for linha in range(2, 5)
            ),
            1250
        )

    def test_dia_sem_movimento(self):
        wb = self.gerar("2026-11-20")

        resumo = wb["Resumo"]

        self.assertEqual(resumo["B3"].value, 0)
        self.assertEqual(resumo["B4"].value, 0)
        self.assertIsNone(resumo["B7"].value)
        self.assertIsNone(resumo["B8"].value)


if __name__ == "__main__":
    unittest.main()
