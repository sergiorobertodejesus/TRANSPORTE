from ambiente_flask import AmbienteFlask


class TestInicializacao(AmbienteFlask):

    def test_pagina_inicial(self):
        resposta = self.cliente.get("/")
        self.assertEqual(resposta.status_code, 200)

    def test_recursos_isolados(self):
        self.assertTrue(self.caminho_banco.is_file())
        self.assertTrue(self.caminho_fotos.is_dir())

        self.assertEqual(
            self.database.DB_PATH,
            self.caminho_banco
        )

        self.assertEqual(
            self.caminho_fotos,
            self.pasta / "instance" / "fotos_jornadas"
        )
