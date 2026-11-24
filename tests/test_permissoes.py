from ambiente_flask import AmbienteFlask


class TestPermissoes(AmbienteFlask):

    def test_acessos_sem_autenticacao(self):
        for rota, destino in (
            ("/painel_admin", "/login_admin"),
            ("/motorista", "/login_motorista"),
            ("/foto_jornada/arquivo_teste.jpg", "/login_motorista"),
        ):
            with self.subTest(rota=rota):
                resposta = self.cliente.get(rota)
                self.assertEqual(resposta.status_code, 302)
                self.assertTrue(
                    resposta.headers["Location"].endswith(destino)
                )

    def test_protecao_csrf(self):
        resposta = self.cliente.post(
            "/jornada",
            data={"acao": "iniciar"}
        )
        self.assertEqual(resposta.status_code, 400)

    def test_sessao_administrativa_inexistente(self):
        with self.cliente.session_transaction() as sessao:
            sessao["administrador_id"] = 999999

        resposta = self.cliente.get("/painel_admin")

        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(
            resposta.headers["Location"].endswith("/login_admin")
        )

    def test_sessao_motorista_inexistente(self):
        with self.cliente.session_transaction() as sessao:
            sessao["motorista_id"] = 999999

        resposta = self.cliente.get("/motorista")

        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(
            resposta.headers["Location"].endswith("/login_motorista")
        )
