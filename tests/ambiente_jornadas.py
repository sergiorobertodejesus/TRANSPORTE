from ambiente_flask import AmbienteFlask, extrair_csrf


class AmbienteJornadas(AmbienteFlask):

    def setUp(self):
        super().setUp()

        db = self.database.conectar()

        try:
            with db:
                cursor = db.execute(
                    "INSERT INTO veiculos (nome, ativo) "
                    "VALUES ('Veiculo Bloqueio Teste', 1)"
                )

                self.veiculo_id = cursor.lastrowid
                self.motoristas = []

                for numero in (1, 2):
                    cursor = db.execute(
                        "INSERT INTO motoristas (nome, ativo) "
                        "VALUES (?, 1)",
                        (f"Motorista Bloqueio {numero}",)
                    )

                    motorista_id = cursor.lastrowid
                    self.motoristas.append(motorista_id)

                    db.execute(
                        "INSERT INTO acessos "
                        "(motorista_id, usuario, senha_hash, ativo) "
                        "VALUES (?, ?, ?, 1)",
                        (
                            motorista_id,
                            f"bloqueio_{numero}",
                            "hash_teste"
                        )
                    )

                    db.execute(
                        "INSERT INTO escalas "
                        "(motorista_id, veiculo_id, "
                        "hora_inicio, hora_fim, ativo) "
                        "VALUES (?, ?, '06:00', '14:00', 1)",
                        (motorista_id, self.veiculo_id)
                    )

                db.execute(
                    "INSERT INTO jornadas "
                    "(motorista_id, veiculo_id, "
                    "data_inicio, km_inicial, status) "
                    "VALUES (?, ?, '2026-11-23T08:00:00', "
                    "1000, 'EM_ANDAMENTO')",
                    (self.motoristas[0], self.veiculo_id)
                )

        finally:
            db.close()

    def acessar_motorista(self, numero):
        with self.cliente.session_transaction() as sessao:
            sessao.clear()
            sessao["motorista_id"] = self.motoristas[numero - 1]
            sessao["nome_motorista"] = (
                f"Motorista Bloqueio {numero}"
            )

        pagina = self.cliente.get("/motorista")
        self.assertEqual(pagina.status_code, 200)

        return extrair_csrf(pagina.data)

    def encerrar_jornada_padrao(self):
        token = self.acessar_motorista(1)

        resposta = self.cliente.post("/jornada", data={
            "acao": "encerrar",
            "csrf_token": token,
            "km_final": "1150",
            "bateria_final": "50",
            "uber_total": "300",
            "uber_dinheiro": "50",
            "99_total": "200",
            "99_dinheiro": "30",
            "corridas_particulares": "0",
            "particulares_dinheiro": "0",
            "uber_pix": "0",
            "99_pix": "0",
            "particulares_pix": "0",
            "pix_empresa": "0",
            "recarga": "40",
            "combustivel": "20",
            "outras_despesas": "10",
            "avaria_final": "nao"
        })

        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(
            resposta.headers["Location"].endswith("/")
        )
