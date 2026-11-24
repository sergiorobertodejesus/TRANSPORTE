"""Infraestrutura compartilhada para testes isolados do Flask."""

import importlib
import os
import sys
import tempfile
import unittest

from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch


class AmbienteFlask(unittest.TestCase):

    def setUp(self):
        self.assertEqual(os.environ.get("ER_AMBIENTE"), "teste")

        import database
        from flask import Flask

        self.database = database

        contextos = ExitStack()
        self.addCleanup(contextos.close)

        temporario = tempfile.TemporaryDirectory(
            prefix="er_flask_teste_"
        )
        self.addCleanup(
            lambda: self.assertFalse(Path(temporario.name).exists())
        )
        self.addCleanup(temporario.cleanup)

        self.pasta = Path(temporario.name)
        self.caminho_banco = self.pasta / "teste.db"

        contextos.enter_context(
            patch.object(database, "DB_PATH", self.caminho_banco)
        )

        contextos.enter_context(
            patch.dict(os.environ, {
                "FLASK_SECRET_KEY": "chave-exclusiva-testes"
            })
        )

        def flask_temporario(*args, **kwargs):
            kwargs["instance_path"] = str(
                self.pasta / "instance"
            )
            return Flask(*args, **kwargs)

        sys.modules.pop("app", None)
        self.addCleanup(sys.modules.pop, "app", None)

        with patch("flask.Flask", flask_temporario):
            self.modulo_app = importlib.import_module("app")

        self.app = self.modulo_app.app
        self.cliente = self.app.test_client()
        self.caminho_fotos = self.modulo_app.PASTA_FOTOS

        self.assertEqual(
            self.caminho_fotos,
            self.pasta / "instance" / "fotos_jornadas"
        )


def extrair_csrf(html):
    from html.parser import HTMLParser

    class Leitor(HTMLParser):
        token = None

        def handle_starttag(self, tag, attrs):
            if tag != "input":
                return
            dados = dict(attrs)
            if dados.get("name") == "csrf_token":
                self.token = dados.get("value")

    leitor = Leitor()
    leitor.feed(html.decode("utf-8"))
    if not leitor.token:
        raise AssertionError("Token CSRF não encontrado")
    return leitor.token
