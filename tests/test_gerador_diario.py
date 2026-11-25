import sqlite3
import tempfile
import unittest

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from openpyxl import load_workbook

import test_relatorio_financeiro

from gerar_relatorio_diario import (
    data_referencia,
    gerar_relatorios,
    FUSO
)


class TestGeradorDiario(unittest.TestCase):

    def setUp(self):
        fixture = (
            test_relatorio_financeiro.TestRelatorioFinanceiro()
        )

        self.addCleanup(fixture.doCleanups)
        fixture.setUp()

        temporario = tempfile.TemporaryDirectory()
        self.addCleanup(temporario.cleanup)

        self.base = Path(temporario.name)
        self.banco = self.base / "teste.db"
        self.destino = self.base / "relatorios"
        self.dia = "2026-11-24"

        with sqlite3.connect(self.banco) as copia:
            fixture.db.backup(copia)

    def gerar(self):
        return gerar_relatorios(
            self.banco,
            self.destino,
            self.dia
        )

    def test_data_automatica(self):
        for hora, minuto, esperado in (
            (5, 30, "2026-11-23"),
            (6, 59, "2026-11-23"),
            (7, 0, "2026-11-24"),
            (15, 0, "2026-11-24"),
        ):
            with self.subTest(hora=hora, minuto=minuto):
                agora = datetime(
                    2026, 11, 25,
                    hora, minuto,
                    tzinfo=FUSO
                )

                self.assertEqual(
                    data_referencia(agora),
                    esperado
                )

    def test_geracao_completa(self):
        pasta = self.gerar()

        self.assertEqual(
            {a.name for a in pasta.iterdir()},
            {
                "01_Relatorio_Financeiro.xlsx",
                "02_Relatorio_Produtividade.xlsx",
                "04_Relatorio_Executivo.pdf"
            }
        )

        for arquivo in pasta.glob("*.xlsx"):
            wb = load_workbook(arquivo)
            self.assertEqual(len(wb.sheetnames), 4)
            wb.close()

        pdf = (
            pasta / "04_Relatorio_Executivo.pdf"
        ).read_bytes()

        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertTrue(pdf.rstrip().endswith(b"%%EOF"))

    def test_banco_preservado(self):
        antes = self.banco.read_bytes()

        self.gerar()

        self.assertEqual(
            antes,
            self.banco.read_bytes()
        )

    def test_duplicidade(self):
        pasta = self.gerar()

        antes = {
            a.name: a.read_bytes()
            for a in pasta.iterdir()
        }

        with self.assertRaises(FileExistsError):
            self.gerar()

        depois = {
            a.name: a.read_bytes()
            for a in pasta.iterdir()
        }

        self.assertEqual(antes, depois)

    def test_falha_na_geracao(self):
        with patch(
            "gerar_relatorio_diario.gerar_pdf_executivo",
            side_effect=RuntimeError("Falha simulada")
        ):
            with self.assertRaises(RuntimeError):
                self.gerar()

        self.assertFalse(
            (self.destino / self.dia).exists()
        )

        self.assertEqual(
            list(self.destino.iterdir()),
            []
        )

        self.assertTrue(self.gerar().is_dir())

    def test_execucoes_simultaneas(self):

        def executar():
            try:
                self.gerar()
                return "sucesso"
            except OSError:
                return "bloqueado"

        with ThreadPoolExecutor(max_workers=2) as pool:
            resultados = list(
                pool.map(lambda _: executar(), range(2))
            )

        self.assertCountEqual(
            resultados,
            ["sucesso", "bloqueado"]
        )

        pasta = self.destino / self.dia

        self.assertEqual(len(list(pasta.iterdir())), 3)

        self.assertEqual(
            list(self.destino.iterdir()),
            [pasta]
        )

    def test_banco_inexistente(self):
        with self.assertRaises(FileNotFoundError):
            gerar_relatorios(
                self.base / "inexistente.db",
                self.destino,
                self.dia
            )


if __name__ == "__main__":
    unittest.main()
