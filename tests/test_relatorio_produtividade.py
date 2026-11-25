import unittest
from decimal import Decimal

import test_relatorio_financeiro

from relatorio_produtividade import (
    calcular_distancia,
    calcular_segundos,
    consolidar_produtividade,
)


class TestRelatorioProdutividade(unittest.TestCase):

    def setUp(self):
        ambiente = test_relatorio_financeiro.TestRelatorioFinanceiro()
        self.addCleanup(ambiente.doCleanups)
        ambiente.setUp()
        self.db = ambiente.db

        self.db.executemany("""
            UPDATE jornadas
            SET data_inicio = ?,
                km_inicial = ?,
                km_final = ?
            WHERE id = ?
        """, [
            ("2026-11-24T06:00:00-03:00", 1000, 1200, 1),
            ("2026-11-24T15:00:00-03:00", 1200, 1360, 2),
            ("2026-11-24T14:00:00-03:00", 2000, 2140, 3),
        ])

    def resultado(self):
        return consolidar_produtividade(
            self.db, "2026-11-24"
        )

    def test_totais_gerais(self):
        geral = self.resultado()["geral"]

        self.assertEqual(geral["jornadas"], 3)
        self.assertEqual(geral["bruto"], Decimal("1250"))
        self.assertEqual(geral["km"], 500)
        self.assertEqual(geral["horas"], 24)
        self.assertEqual(geral["reais_km"], Decimal("2.50"))
        self.assertEqual(geral["reais_hora"], Decimal("52.08"))

    def test_motoristas(self):
        motoristas = self.resultado()["motoristas"]

        a = motoristas[(1, "Motorista A")]
        b = motoristas[(2, "Motorista B")]

        self.assertEqual(a["km"], 340)
        self.assertEqual(a["horas"], 16)
        self.assertEqual(a["reais_hora"], Decimal("53.12"))

        self.assertEqual(b["km"], 160)
        self.assertEqual(b["horas"], 8)
        self.assertEqual(b["reais_hora"], Decimal("50.00"))

    def test_veiculos(self):
        veiculos = self.resultado()["veiculos"]

        gs = veiculos[(1, "GS", "TESTE01")]
        polo = veiculos[(2, "Polo", "TESTE02")]

        self.assertEqual(gs["km"], 360)
        self.assertEqual(gs["reais_hora"], Decimal("56.25"))

        self.assertEqual(polo["km"], 140)
        self.assertEqual(polo["reais_hora"], Decimal("43.75"))

    def test_distancias_invalidas(self):
        self.assertIsNone(calcular_distancia(None, 100))
        self.assertIsNone(calcular_distancia(200, 100))
        self.assertIsNone(calcular_distancia(-10, 100))
        self.assertEqual(calcular_distancia(100, 100), 0)
        self.assertEqual(calcular_distancia(100, 250), 150)

    def test_horarios_e_fusos(self):
        self.assertEqual(
            calcular_segundos(
                "2026-11-24T22:00:00-03:00",
                "2026-11-25T05:00:00+00:00"
            ),
            14400
        )

        self.assertIsNone(
            calcular_segundos(None, None)
        )

        self.assertIsNone(
            calcular_segundos(
                "2026-11-24T06:00:00",
                "2026-11-24T14:00:00"
            )
        )

        self.assertIsNone(
            calcular_segundos(
                "2026-11-24T14:00:00-03:00",
                "2026-11-24T06:00:00-03:00"
            )
        )

    def test_consolidacao_com_dados_invalidos(self):
        self.db.execute("""
            UPDATE jornadas
            SET km_final = NULL,
                data_inicio = NULL
            WHERE id = 1
        """)

        geral = self.resultado()["geral"]

        self.assertEqual(geral["bruto"], Decimal("1250"))
        self.assertEqual(geral["km_invalidos"], 1)
        self.assertEqual(geral["horarios_invalidos"], 1)
        self.assertEqual(geral["km"], 300)
        self.assertEqual(geral["horas"], 16)
        self.assertEqual(geral["bruto_km"], Decimal("750"))
        self.assertEqual(geral["bruto_horas"], Decimal("750"))
        self.assertEqual(geral["reais_km"], Decimal("2.50"))
        self.assertEqual(geral["reais_hora"], Decimal("46.88"))

    def test_distancia_zero(self):
        self.db.execute("""
            UPDATE jornadas
            SET km_final = km_inicial
            WHERE id = 1
        """)

        resultado = self.resultado()
        geral = resultado["geral"]

        self.assertEqual(geral["km"], 300)
        self.assertEqual(geral["bruto_km"], Decimal("750"))
        self.assertIsNone(
            resultado["jornadas"][0]["reais_km"]
        )

    def test_dia_sem_movimento(self):
        resultado = consolidar_produtividade(
            self.db, "2026-11-20"
        )

        geral = resultado["geral"]

        self.assertEqual(geral["jornadas"], 0)
        self.assertEqual(geral["km"], 0)
        self.assertEqual(geral["horas"], 0)
        self.assertIsNone(geral["reais_km"])
        self.assertIsNone(geral["reais_hora"])
        self.assertEqual(resultado["jornadas"], [])
