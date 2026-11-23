import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


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

                    # Verificar acessos sem autenticação.
                    for rota, destino in (
                        ("/painel_admin", "/login_admin"),
                        ("/motorista", "/login_motorista"),
                        ("/foto_jornada/arquivo_teste.jpg", "/login_motorista"),
                    ):
                        with self.subTest(rota=rota):
                            resposta = cliente.get(rota)
                            self.assertEqual(resposta.status_code, 302)
                            self.assertTrue(
                                resposta.headers["Location"].endswith(destino)
                            )

                    # POST sem token CSRF deve ser bloqueado.
                    resposta = cliente.post(
                        "/jornada",
                        data={"acao": "iniciar"}
                    )
                    self.assertEqual(resposta.status_code, 400)


                    # Sessão administrativa inexistente.
                    with cliente.session_transaction() as sessao:
                        sessao["administrador_id"] = 999999

                    resposta = cliente.get("/painel_admin")
                    self.assertEqual(resposta.status_code, 302)
                    self.assertTrue(
                        resposta.headers["Location"].endswith("/login_admin")
                    )

                    # Sessão de motorista inexistente.
                    with cliente.session_transaction() as sessao:
                        sessao.clear()
                        sessao["motorista_id"] = 999999

                    resposta = cliente.get("/motorista")
                    self.assertEqual(resposta.status_code, 302)
                    self.assertTrue(
                        resposta.headers["Location"].endswith("/login_motorista")
                    )


                    # Criar usuários fictícios no banco temporário.
                    from werkzeug.security import generate_password_hash

                    db = database.conectar()
                    try:
                        cursor = db.execute(
                            "INSERT INTO administradores "
                            "(usuario, senha_hash, ativo) VALUES (?, ?, 1)",
                            ("admin_teste", generate_password_hash("senha_teste"))
                        )
                        admin_id = cursor.lastrowid

                        cursor = db.execute(
                            "INSERT INTO motoristas (nome, ativo) VALUES (?, 1)",
                            ("Motorista Teste",)
                        )
                        motorista_id = cursor.lastrowid

                        db.execute(
                            "INSERT INTO acessos "
                            "(motorista_id, usuario, senha_hash, ativo) "
                            "VALUES (?, ?, ?, 1)",
                            (
                                motorista_id,
                                "motorista_teste",
                                generate_password_hash("senha_teste")
                            )
                        )
                        db.commit()
                    finally:
                        db.close()

                    # Motorista válido não acessa painel administrativo.
                    with cliente.session_transaction() as sessao:
                        sessao.clear()
                        sessao["motorista_id"] = motorista_id
                        sessao["nome_motorista"] = "Motorista Teste"

                    resposta = cliente.get("/painel_admin")
                    self.assertEqual(resposta.status_code, 302)
                    self.assertTrue(
                        resposta.headers["Location"].endswith("/login_admin")
                    )

                    # Administrador válido não acessa área do motorista.
                    with cliente.session_transaction() as sessao:
                        sessao.clear()
                        sessao["administrador_id"] = admin_id
                        sessao["administrador_usuario"] = "admin_teste"

                    resposta = cliente.get("/motorista")
                    self.assertEqual(resposta.status_code, 302)
                    self.assertTrue(
                        resposta.headers["Location"].endswith("/login_motorista")
                    )


                    # Login administrativo com senha correta e CSRF ativo.
                    with cliente.session_transaction() as sessao:
                        sessao.clear()

                    resposta = cliente.get("/login_admin")
                    self.assertEqual(resposta.status_code, 200)

                    token = extrair_csrf(resposta.data)

                    resposta = cliente.post(
                        "/login_admin",
                        data={
                            "usuario": "admin_teste",
                            "senha": "senha_teste",
                            "csrf_token": token
                        }
                    )

                    self.assertEqual(resposta.status_code, 302)
                    self.assertTrue(
                        resposta.headers["Location"].endswith("/painel_admin")
                    )

                    with cliente.session_transaction() as sessao:
                        self.assertEqual(
                            sessao.get("administrador_id"), admin_id
                        )


                    # Senha administrativa incorreta.
                    with cliente.session_transaction() as sessao:
                        sessao.clear()

                    resposta = cliente.get("/login_admin")
                    token = extrair_csrf(resposta.data)

                    resposta = cliente.post("/login_admin", data={
                        "usuario": "admin_teste",
                        "senha": "senha_incorreta",
                        "csrf_token": token
                    })

                    self.assertEqual(resposta.status_code, 200)
                    self.assertIn(b"inv", resposta.data.lower())

                    with cliente.session_transaction() as sessao:
                        self.assertNotIn("administrador_id", sessao)


                    # Testar login do motorista.
                    for senha, sucesso in (
                        ("senha_teste", True),
                        ("senha_incorreta", False),
                    ):
                        with self.subTest(senha_correta=sucesso):
                            with cliente.session_transaction() as sessao:
                                sessao.clear()

                            resposta = cliente.get("/login_motorista")
                            token = extrair_csrf(resposta.data)

                            resposta = cliente.post("/login_motorista", data={
                                "usuario": "motorista_teste",
                                "senha": senha,
                                "csrf_token": token
                            })

                            self.assertEqual(
                                resposta.status_code, 302 if sucesso else 200
                            )
                            with cliente.session_transaction() as sessao:
                                self.assertEqual(
                                    sessao.get("motorista_id"),
                                    motorista_id if sucesso else None
                                )


                    # Contas desativadas não podem fazer login.
                    db = database.conectar()
                    try:
                        db.execute(
                            "UPDATE administradores SET ativo = 0 WHERE id = ?",
                            (admin_id,)
                        )
                        db.execute(
                            "UPDATE motoristas SET ativo = 0 WHERE id = ?",
                            (motorista_id,)
                        )
                        db.commit()
                    finally:
                        db.close()

                    for rota, usuario, chave_sessao in (
                        ("/login_admin", "admin_teste", "administrador_id"),
                        ("/login_motorista", "motorista_teste", "motorista_id"),
                    ):
                        with self.subTest(conta_desativada=usuario):
                            with cliente.session_transaction() as sessao:
                                sessao.clear()

                            resposta = cliente.get(rota)
                            token = extrair_csrf(resposta.data)

                            resposta = cliente.post(rota, data={
                                "usuario": usuario,
                                "senha": "senha_teste",
                                "csrf_token": token
                            })

                            self.assertEqual(resposta.status_code, 200)
                            with cliente.session_transaction() as sessao:
                                self.assertNotIn(chave_sessao, sessao)

                    # Limpar sessão após as verificações.
                    with cliente.session_transaction() as sessao:
                        sessao.clear()

                    self.assertTrue(caminho_banco.exists())
                    self.assertTrue(caminho_fotos.is_dir())



        self.assertFalse(caminho_banco.exists())
        self.assertFalse(caminho_fotos.exists())


if __name__ == "__main__":
    unittest.main()
