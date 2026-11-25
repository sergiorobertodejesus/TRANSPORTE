import unittest
from io import BytesIO
from decimal import Decimal

from openpyxl import load_workbook
import test_relatorio_financeiro
from relatorio_financeiro import consolidar_financeiro
from excel_financeiro import gerar_excel_financeiro


class TestExcelFinanceiro(unittest.TestCase):

    def setUp(self):
        ambiente = test_relatorio_financeiro.TestRelatorioFinanceiro()
        self.addCleanup(ambiente.doCleanups)
        ambiente.setUp()
        self.db = ambiente.db

    def gerar_planilha(self, dia):
        resultado = consolidar_financeiro(self.db, dia)

        memoria = BytesIO()
        gerar_excel_financeiro(resultado, memoria)
        memoria.seek(0)

        wb = load_workbook(memoria)
        self.addCleanup(wb.close)

        return wb

    def test_integracao_periodos(self):
        self.db.execute("""
            UPDATE jornadas
            SET data_fim = ?
            WHERE id = 3
        """, ("2026-11-25T05:00:00+00:00",))

        self.db.execute("""
            UPDATE jornadas
            SET data_fim = ?
            WHERE id = 2
        """, ("2026-11-25T10:00:00+00:00",))

        anterior = consolidar_financeiro(
            self.db, "2026-11-24"
        )["geral"]

        seguinte = consolidar_financeiro(
            self.db, "2026-11-25"
        )["geral"]

        self.assertEqual(anterior["jornadas"], 2)
        self.assertEqual(anterior["bruto"], Decimal("850"))
        self.assertEqual(seguinte["jornadas"], 1)
        self.assertEqual(seguinte["bruto"], Decimal("400"))

        self.assertEqual(
            anterior["bruto"] + seguinte["bruto"],
            Decimal("1250")
        )

    def test_abas_e_graficos(self):
        wb = self.gerar_planilha("2026-11-24")

        self.assertEqual(wb.sheetnames, [
            "Resumo",
            "Motoristas",
            "Veículos",
            "Recargas e combustíveis"
        ])

        self.assertEqual(len(wb["Resumo"]._charts), 2)
        self.assertEqual(len(wb["Motoristas"]._charts), 1)
        self.assertEqual(len(wb["Veículos"]._charts), 0)
        self.assertEqual(
            len(wb["Recargas e combustíveis"]._charts), 1
        )

    def test_valores_financeiros(self):
        wb = self.gerar_planilha("2026-11-24")

        resumo = wb["Resumo"]

        self.assertEqual(resumo["B3"].value, 3)
        self.assertEqual(resumo["B4"].value, 1250)
        self.assertEqual(resumo["B5"].value, 180)
        self.assertEqual(resumo["B6"].value, 1070)
        self.assertEqual(resumo["B9"].value, 90)
        self.assertEqual(resumo["B10"].value, 70)
        self.assertEqual(resumo["B11"].value, 20)

        motoristas = wb["Motoristas"]
        veiculos = wb["Veículos"]
        energia = wb["Recargas e combustíveis"]

        self.assertEqual(motoristas["C4"].value, 1250)
        self.assertEqual(motoristas["E4"].value, 1070)

        self.assertEqual(veiculos["D4"].value, 1250)
        self.assertEqual(veiculos["E4"].value, 180)
        self.assertEqual(veiculos["F4"].value, 1070)

        self.assertEqual(energia["C4"].value, 90)
        self.assertEqual(energia["D4"].value, 70)
        self.assertEqual(energia["E4"].value, 160)

    def test_excel_sem_movimento(self):
        wb = self.gerar_planilha("2026-11-20")

        self.assertEqual(len(wb.sheetnames), 4)
        self.assertEqual(wb["Resumo"]["B3"].value, 0)
        self.assertEqual(wb["Resumo"]["B4"].value, 0)
        self.assertEqual(wb["Resumo"]["B6"].value, 0)

        for aba in wb.worksheets:
            self.assertEqual(len(aba._charts), 0)
