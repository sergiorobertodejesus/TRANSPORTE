import sqlite3
import unittest

from datetime import timedelta
from periodo_operacional import limites_operacionais
from relatorio_financeiro import consolidar_financeiro


class TestPeriodoOperacional(unittest.TestCase):

    def test_limites_operacionais(self):
        inicio, fim = limites_operacionais("2026-11-24")

        self.assertEqual(
            inicio.isoformat(),
            "2026-11-24T07:00:00-03:00"
        )

        self.assertEqual(
            fim.isoformat(),
            "2026-11-25T07:00:00-03:00"
        )

        self.assertEqual(
            fim - inicio, timedelta(hours=24)
        )

    def test_fronteiras_e_fusos(self):
        db = sqlite3.connect(":memory:")
        self.addCleanup(db.close)

        inicio, fim = limites_operacionais("2026-11-24")

        casos = (
            ("2026-11-24T06:59:59-03:00", False),
            ("2026-11-24T07:00:00-03:00", True),
            ("2026-11-24T23:59:59-03:00", True),
            ("2026-11-25T02:00:00-03:00", True),
            ("2026-11-25T06:59:59-03:00", True),
            ("2026-11-25T07:00:00-03:00", False),
            ("2026-11-24T09:59:59+00:00", False),
            ("2026-11-24T10:00:00+00:00", True),
            ("2026-11-25T09:59:59+00:00", True),
            ("2026-11-25T10:00:00+00:00", False),
        )

        for horario, esperado in casos:
            with self.subTest(horario=horario):
                resultado = db.execute("""
                    SELECT julianday(?) >= julianday(?)
                       AND julianday(?) < julianday(?)
                """, (
                    horario, inicio.isoformat(),
                    horario, fim.isoformat()
                )).fetchone()[0]

                self.assertEqual(bool(resultado), esperado)

    def test_periodos_consecutivos(self):
        _, fim = limites_operacionais("2026-11-24")
        inicio, _ = limites_operacionais("2026-11-25")

        self.assertEqual(fim, inicio)

    def test_virada_do_ano(self):
        _, fim = limites_operacionais("2026-12-31")

        self.assertEqual(
            fim.isoformat(),
            "2027-01-01T07:00:00-03:00"
        )
