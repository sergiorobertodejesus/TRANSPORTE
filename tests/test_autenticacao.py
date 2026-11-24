from ambiente_flask import AmbienteFlask
from ambiente_flask import extrair_csrf
from werkzeug.security import generate_password_hash


class TestAutenticacao(AmbienteFlask):

    def setUp(self):
        super().setUp()

        senha_hash = generate_password_hash("senha_teste")

        db = self.database.conectar()
        try:
            with db:
                cursor = db.execute(
                    "INSERT INTO administradores "
                    "(usuario, senha_hash, ativo) VALUES (?, ?, 1)",
                    ("admin_teste", senha_hash)
                )
                self.admin_id = cursor.lastrowid

                cursor = db.execute(
                    "INSERT INTO motoristas (nome, ativo) "
                    "VALUES (?, 1)",
                    ("Motorista Teste",)
                )
                self.motorista_id = cursor.lastrowid

                db.execute(
                    "INSERT INTO acessos "
                    "(motorista_id, usuario, senha_hash, ativo) "
                    "VALUES (?, ?, ?, 1)",
                    (self.motorista_id, "motorista_teste", senha_hash)
                )
        finally:
            db.close()

    def realizar_login(self, rota, usuario, senha):
        pagina = self.cliente.get(rota)
        self.assertEqual(pagina.status_code, 200)

        return self.cliente.post(rota, data={
            "usuario": usuario,
            "senha": senha,
            "csrf_token": extrair_csrf(pagina.data)
        })

    def test_login_admin_valido(self):
        resposta = self.realizar_login(
            "/login_admin", "admin_teste", "senha_teste"
        )

        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(
            resposta.headers["Location"].endswith("/painel_admin")
        )

        with self.cliente.session_transaction() as sessao:
            self.assertEqual(
                sessao.get("administrador_id"), self.admin_id
            )

    def test_login_admin_invalido(self):
        resposta = self.realizar_login(
            "/login_admin", "admin_teste", "senha_incorreta"
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertIn(b"inv", resposta.data.lower())

        with self.cliente.session_transaction() as sessao:
            self.assertNotIn("administrador_id", sessao)

    def test_login_motorista_valido(self):
        resposta = self.realizar_login(
            "/login_motorista", "motorista_teste", "senha_teste"
        )

        self.assertEqual(resposta.status_code, 302)

        with self.cliente.session_transaction() as sessao:
            self.assertEqual(
                sessao.get("motorista_id"), self.motorista_id
            )

    def test_login_motorista_invalido(self):
        resposta = self.realizar_login(
            "/login_motorista", "motorista_teste", "senha_incorreta"
        )

        self.assertEqual(resposta.status_code, 200)

        with self.cliente.session_transaction() as sessao:
            self.assertNotIn("motorista_id", sessao)

    def test_contas_desativadas(self):
        db = self.database.conectar()
        try:
            with db:
                db.execute(
                    "UPDATE administradores SET ativo = 0 WHERE id = ?",
                    (self.admin_id,)
                )
                db.execute(
                    "UPDATE motoristas SET ativo = 0 WHERE id = ?",
                    (self.motorista_id,)
                )
        finally:
            db.close()

        for rota, usuario, chave in (
            ("/login_admin", "admin_teste", "administrador_id"),
            ("/login_motorista", "motorista_teste", "motorista_id"),
        ):
            with self.subTest(usuario=usuario):
                with self.cliente.session_transaction() as sessao:
                    sessao.clear()

                resposta = self.realizar_login(
                    rota, usuario, "senha_teste"
                )

                self.assertEqual(resposta.status_code, 200)

                with self.cliente.session_transaction() as sessao:
                    self.assertNotIn(chave, sessao)

    def test_motorista_sem_permissao_administrativa(self):
        with self.cliente.session_transaction() as sessao:
            sessao["motorista_id"] = self.motorista_id
            sessao["nome_motorista"] = "Motorista Teste"

        resposta = self.cliente.get("/painel_admin")

        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(
            resposta.headers["Location"].endswith("/login_admin")
        )

    def test_admin_sem_permissao_de_motorista(self):
        with self.cliente.session_transaction() as sessao:
            sessao["administrador_id"] = self.admin_id
            sessao["administrador_usuario"] = "admin_teste"

        resposta = self.cliente.get("/motorista")

        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(
            resposta.headers["Location"].endswith("/login_motorista")
        )
