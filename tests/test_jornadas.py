from ambiente_jornadas import AmbienteJornadas


class TestJornadas(AmbienteJornadas):

    def test_veiculo_ocupado(self):
        token = self.acessar_motorista(2)

        itens = (
            "retrovisores", "farol_alto",
            "seta_dianteira", "seta_traseira",
            "luz_freio", "brake_light", "pneus",
            "avarias_bancos", "avarias_painel",
            "riscos_portas", "outras_avarias"
        )

        dados = {
            "acao": "iniciar",
            "km_inicial": "1100",
            "bateria_inicial": "80",
            "csrf_token": token
        }

        dados.update({item: "sim" for item in itens})

        resposta = self.cliente.post(
            "/jornada", data=dados
        )

        self.assertEqual(resposta.status_code, 302)

        with self.cliente.session_transaction() as sessao:
            mensagens = sessao.get("_flashes", [])

            self.assertTrue(any(
                "veículo já possui uma jornada" in mensagem
                for _, mensagem in mensagens
            ))

        db = self.database.conectar()

        try:
            jornadas = db.execute(
                "SELECT motorista_id, status "
                "FROM jornadas ORDER BY id"
            ).fetchall()

            self.assertEqual(len(jornadas), 1)

            self.assertEqual(
                jornadas[0]["motorista_id"],
                self.motoristas[0]
            )

            self.assertEqual(
                jornadas[0]["status"], "EM_ANDAMENTO"
            )

        finally:
            db.close()

    def test_encerramentos_invalidos(self):
        token = self.acessar_motorista(1)

        cenarios = (
            (
                {"km_final": "999"},
                "quilometragem final não pode ser menor"
            ),
            (
                {"uber_total": "-100"},
                "Confira os valores financeiros"
            ),
            (
                {"avaria_final": "sim"},
                "Descreva a avaria"
            ),
        )

        for alteracoes, mensagem in cenarios:
            with self.subTest(validacao=alteracoes):
                dados = {
                    "acao": "encerrar",
                    "csrf_token": token,
                    "km_final": "1150",
                    "bateria_final": "50",
                    "uber_total": "300",
                    "recarga": "40",
                    "avaria_final": "nao"
                }
                dados.update(alteracoes)

                resposta = self.cliente.post(
                    "/jornada", data=dados
                )

                self.assertEqual(
                    resposta.status_code, 302
                )

                with self.cliente.session_transaction() as sessao:
                    mensagens = sessao.pop("_flashes", [])
                    self.assertTrue(any(
                        mensagem in aviso
                        for _, aviso in mensagens
                    ))

                db = self.database.conectar()
                try:
                    jornada = db.execute(
                        "SELECT id, status FROM jornadas "
                        "WHERE motorista_id = ?",
                        (self.motoristas[0],)
                    ).fetchone()

                    self.assertEqual(
                        jornada["status"], "EM_ANDAMENTO"
                    )

                    for tabela in ("ganhos", "despesas"):
                        total = db.execute(
                            f"SELECT COUNT(*) FROM {tabela} "
                            "WHERE jornada_id = ?",
                            (jornada["id"],)
                        ).fetchone()[0]

                        self.assertEqual(total, 0)
                finally:
                    db.close()

    def test_encerramento_valido(self):
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

        db = self.database.conectar()
        try:
            jornada = db.execute(
                "SELECT status, km_inicial, km_final "
                "FROM jornadas WHERE motorista_id = ?",
                (self.motoristas[0],)
            ).fetchone()

            self.assertEqual(
                jornada["status"], "ENCERRADA"
            )
            self.assertEqual(jornada["km_inicial"], 1000)
            self.assertEqual(jornada["km_final"], 1150)

            ganhos = db.execute(
                "SELECT uber_total, noventa_nove_total, "
                "dinheiro_total FROM ganhos "
                "WHERE jornada_id = ("
                "SELECT id FROM jornadas "
                "WHERE motorista_id = ?)",
                (self.motoristas[0],)
            ).fetchone()

            self.assertAlmostEqual(
                ganhos["uber_total"], 300
            )
            self.assertAlmostEqual(
                ganhos["noventa_nove_total"], 200
            )
            self.assertAlmostEqual(
                ganhos["dinheiro_total"], 80
            )

            despesas = db.execute(
                "SELECT SUM(valor) AS total "
                "FROM despesas WHERE jornada_id = ("
                "SELECT id FROM jornadas "
                "WHERE motorista_id = ?)",
                (self.motoristas[0],)
            ).fetchone()

            self.assertAlmostEqual(
                despesas["total"], 70
            )
        finally:
            db.close()
