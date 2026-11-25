import shutil
import subprocess
import tempfile
import unittest

from pathlib import Path

import test_relatorio_produtividade

from relatorio_financeiro import consolidar_financeiro
from relatorio_produtividade import consolidar_produtividade
from pdf_executivo import gerar_pdf_executivo


class TestPDFExecutivo(unittest.TestCase):

    def setUp(self):
        fixture = (
            test_relatorio_produtividade.TestRelatorioProdutividade()
        )

        self.addCleanup(fixture.doCleanups)
        fixture.setUp()

        self.db = fixture.db

        temporario = tempfile.TemporaryDirectory()
        self.addCleanup(temporario.cleanup)

        self.arquivo = (
            Path(temporario.name) / "executivo.pdf"
        )

    def gerar(self, dia="2026-11-24"):
        financeiro = consolidar_financeiro(
            self.db, dia
        )

        produtividade = consolidar_produtividade(
            self.db, dia
        )

        gerar_pdf_executivo(
            financeiro,
            produtividade,
            self.arquivo
        )

        return self.arquivo

    def test_estrutura_pdf(self):
        dados = self.gerar().read_bytes()

        self.assertTrue(dados.startswith(b"%PDF-"))
        self.assertTrue(dados.rstrip().endswith(b"%%EOF"))

    @unittest.skipUnless(
        shutil.which("pdfinfo"),
        "pdfinfo indisponivel"
    )
    def test_paginacao(self):
        arquivo = self.gerar()

        resultado = subprocess.check_output(
            ["pdfinfo", str(arquivo)],
            text=True
        )

        paginas = next(
            linha.split(":")[1].strip()
            for linha in resultado.splitlines()
            if linha.startswith("Pages:")
        )

        self.assertEqual(int(paginas), 3)

    @unittest.skipUnless(
        shutil.which("pdftotext"),
        "pdftotext indisponivel"
    )
    def test_conteudo_financeiro(self):
        arquivo = self.gerar()

        texto = subprocess.check_output(
            ["pdftotext", str(arquivo), "-"],
            text=True
        )

        for valor in (
            "1.250,00",
            "1.070,00",
            "180,00",
            "90,00",
            "70,00"
        ):
            with self.subTest(valor=valor):
                self.assertIn(valor, texto)

    def test_dia_sem_movimento(self):
        arquivo = self.gerar("2026-11-20")

        self.assertTrue(arquivo.is_file())
        self.assertGreater(arquivo.stat().st_size, 0)

    def test_relatorios_divergentes(self):
        financeiro = consolidar_financeiro(
            self.db, "2026-11-24"
        )

        produtividade = consolidar_produtividade(
            self.db, "2026-11-23"
        )

        with self.assertRaises(ValueError):
            gerar_pdf_executivo(
                financeiro,
                produtividade,
                self.arquivo
            )


if __name__ == "__main__":
    unittest.main()
