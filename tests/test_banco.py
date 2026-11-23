import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database


class TestBanco(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if os.environ.get("ER_AMBIENTE") != "teste":
            raise RuntimeError(
                "Testes bloqueados: defina ER_AMBIENTE=teste."
            )


    def test_inicializacao_banco_temporario(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "teste_automatizado.db"

            with patch.object(database, "DB_PATH", caminho):
                database.inicializar_banco()

                with database.conectar() as conexao:
                    integridade = conexao.execute(
                        "PRAGMA integrity_check"
                    ).fetchone()[0]

                    tabelas = {
                        linha[0]
                        for linha in conexao.execute(
                            "SELECT name FROM sqlite_master "
                            "WHERE type = 'table'"
                        )
                    }

                self.assertEqual(integridade, "ok")
                self.assertIn("motoristas", tabelas)
                self.assertIn("veiculos", tabelas)
                self.assertIn("jornadas", tabelas)

            self.assertTrue(caminho.exists())

        self.assertFalse(caminho.exists())


if __name__ == "__main__":
    unittest.main()
