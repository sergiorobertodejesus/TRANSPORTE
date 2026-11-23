import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class TestFlaskIsolado(unittest.TestCase):

    def test_inicializacao_isolada(self):
        self.assertEqual(os.environ.get("ER_AMBIENTE"), "teste")

        with tempfile.TemporaryDirectory() as pasta:
            caminho_banco = Path(pasta) / "flask_teste.db"
            caminho_fotos = Path(pasta) / "fotos"

            import database

            with patch.object(database, "DB_PATH", caminho_banco):
                with patch.dict(
                    os.environ,
                    {"FLASK_SECRET_KEY": "chave-exclusiva-testes"}
                ):
                    from flask import Flask

                    flask_original = Flask

                    def flask_temporario(*args, **kwargs):
                        kwargs["instance_path"] = str(
                            Path(pasta) / "instance"
                        )
                        return flask_original(*args, **kwargs)

                    self.addCleanup(sys.modules.pop, "app", None)

                    with patch("flask.Flask", flask_temporario):
                        import app as modulo_app

                    caminho_fotos = modulo_app.PASTA_FOTOS

                    self.assertEqual(
                        caminho_fotos,
                        Path(pasta) / "instance" / "fotos_jornadas"
                    )

                    cliente = modulo_app.app.test_client()
                    resposta = cliente.get("/")

                    self.assertEqual(resposta.status_code, 200)
                    self.assertTrue(caminho_banco.exists())
                    self.assertTrue(caminho_fotos.is_dir())



        self.assertFalse(caminho_banco.exists())
        self.assertFalse(caminho_fotos.exists())


if __name__ == "__main__":
    unittest.main()
