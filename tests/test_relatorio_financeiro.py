import sqlite3
import unittest
from decimal import Decimal

from relatorio_financeiro import consolidar_financeiro


class TestRelatorioFinanceiro(unittest.TestCase):

    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.addCleanup(self.db.close)

        self.db.executescript("""
            CREATE TABLE motoristas (
                id INTEGER PRIMARY KEY,
                nome TEXT
            );

            CREATE TABLE veiculos (
                id INTEGER PRIMARY KEY,
                nome TEXT,
                placa TEXT
            );

            CREATE TABLE jornadas (
                id INTEGER PRIMARY KEY,
                motorista_id INTEGER,
                veiculo_id INTEGER,
                data_inicio TEXT,
                km_inicial INTEGER,
                km_final INTEGER,
                data_fim TEXT,
                status TEXT
            );

            CREATE TABLE ganhos (
                jornada_id INTEGER,
                uber_total REAL,
                noventa_nove_total REAL,
                corridas_particulares REAL
            );

            CREATE TABLE despesas (
                jornada_id INTEGER,
                categoria TEXT,
                valor REAL
            );

            INSERT INTO motoristas VALUES
                (1, 'Motorista A'),
                (2, 'Motorista B');

            INSERT INTO veiculos VALUES
                (1, 'GS', 'TESTE01'),
                (2, 'Polo', 'TESTE02');

            INSERT INTO jornadas (
                id, motorista_id, veiculo_id,
                data_fim, status
            ) VALUES
                (1, 1, 1, '2026-11-24T14:00:00-03:00', 'ENCERRADA'),
                (2, 2, 1, '2026-11-24T23:00:00-03:00', 'ENCERRADA'),
                (3, 1, 2, '2026-11-24T22:00:00-03:00', 'ENCERRADA'),
                (4, 2, 2, NULL, 'EM_ANDAMENTO'),
                (5, 1, 1, '2026-11-23T14:00:00-03:00', 'ENCERRADA');

            INSERT INTO ganhos VALUES
                (1, 300, 150, 50),
                (2, 250, 150, 0),
                (3, 200, 150, 0),
                (4, 999, 999, 0),
                (5, 999, 999, 0);

            INSERT INTO despesas VALUES
                (1, 'Recarga elétrica', 50),
                (1, 'Outras despesas', 20),
                (2, 'Recarga elétrica', 40),
                (3, 'Combustível', 70),
                (4, 'Combustível', 999),
                (5, 'Recarga elétrica', 999);
        """)

    def test_totais_gerais(self):
        resultado = consolidar_financeiro(
            self.db, "2026-11-24"
        )

        geral = resultado["geral"]

        esperado = {
            "jornadas": 3,
            "bruto": 1250,
            "despesas": 180,
            "liquido": 1070,
            "recarga": 90,
            "combustivel": 70,
            "outras_despesas": 20,
        }

        for campo, valor in esperado.items():
            with self.subTest(campo=campo):
                self.assertEqual(
                    geral[campo], Decimal(str(valor))
                )

    def test_totais_motoristas(self):
        resultado = consolidar_financeiro(
            self.db, "2026-11-24"
        )

        motoristas = resultado["motoristas"]

        a = motoristas[(1, "Motorista A")]
        b = motoristas[(2, "Motorista B")]

        self.assertEqual(a["bruto"], Decimal("850"))
        self.assertEqual(a["liquido"], Decimal("710"))
        self.assertEqual(b["bruto"], Decimal("400"))
        self.assertEqual(b["liquido"], Decimal("360"))

    def test_totais_veiculos(self):
        resultado = consolidar_financeiro(
            self.db, "2026-11-24"
        )

        veiculos = resultado["veiculos"]

        gs = veiculos[(1, "GS", "TESTE01")]
        polo = veiculos[(2, "Polo", "TESTE02")]

        self.assertEqual(gs["bruto"], Decimal("900"))
        self.assertEqual(gs["liquido"], Decimal("790"))
        self.assertEqual(gs["recarga"], Decimal("90"))

        self.assertEqual(polo["bruto"], Decimal("350"))
        self.assertEqual(polo["liquido"], Decimal("280"))
        self.assertEqual(polo["combustivel"], Decimal("70"))

    def test_dia_sem_movimento(self):
        resultado = consolidar_financeiro(
            self.db, "2026-11-20"
        )

        self.assertEqual(resultado["geral"]["jornadas"], 0)
        self.assertEqual(resultado["geral"]["bruto"], 0)
        self.assertEqual(resultado["motoristas"], {})
        self.assertEqual(resultado["veiculos"], {})
