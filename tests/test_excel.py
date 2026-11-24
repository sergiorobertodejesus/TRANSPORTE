from ambiente_jornadas import AmbienteJornadas


class TestExcel(AmbienteJornadas):

    def test_exportacao_e_filtros(self):
        self.encerrar_jornada_padrao()

        from io import BytesIO
        from openpyxl import load_workbook
        from werkzeug.security import generate_password_hash

        rota = "/exportar_relatorio_excel"

        with self.cliente.session_transaction() as sessao:
            sessao.clear()

        resposta = self.cliente.get(rota)
        self.assertEqual(resposta.status_code, 302)

        with self.cliente.session_transaction() as sessao:
            sessao["motorista_id"] = self.motoristas[0]
            sessao["nome_motorista"] = "Motorista Bloqueio 1"

        resposta = self.cliente.get(rota)
        self.assertEqual(resposta.status_code, 302)

        db = self.database.conectar()
        try:
            with db:
                cursor = db.execute(
                    "INSERT INTO administradores "
                    "(usuario, senha_hash, ativo) "
                    "VALUES (?, ?, 1)",
                    (
                        "admin_excel_teste",
                        generate_password_hash("senha_teste")
                    )
                )
                admin_id = cursor.lastrowid
        finally:
            db.close()

        with self.cliente.session_transaction() as sessao:
            sessao.clear()
            sessao["administrador_id"] = admin_id
            sessao["nome_administrador"] = "Admin Excel Teste"

        def conferir_excel(filtros, quantidade):
            resposta = self.cliente.get(
                rota, query_string=filtros
            )

            self.assertEqual(resposta.status_code, 200)
            self.assertIn(
                "spreadsheetml", resposta.mimetype
            )

            wb = load_workbook(
                BytesIO(resposta.data), data_only=True
            )
            try:
                self.assertEqual(
                    wb.sheetnames,
                    ["Resumo", "Jornadas", "Ganhos",
                     "Despesas", "Avarias"]
                )

                resumo = wb["Resumo"]

                self.assertEqual(
                    resumo["B9"].value, quantidade
                )
                self.assertAlmostEqual(
                    resumo["B10"].value, 500 * quantidade
                )
                self.assertAlmostEqual(
                    resumo["B11"].value, 70 * quantidade
                )
                self.assertAlmostEqual(
                    resumo["B12"].value, 430 * quantidade
                )

                if quantidade:
                    self.assertEqual(
                        wb["Jornadas"]["J2"].value, 150
                    )
            finally:
                wb.close()

        conferir_excel({}, 1)

        filtros_validos = (
            {"motorista_id": self.motoristas[0]},
            {"veiculo_id": self.veiculo_id},
            {"data_inicio": "2026-11-23"},
            {"data_fim": "2026-11-23"},
        )

        for filtro in filtros_validos:
            with self.subTest(filtro=filtro):
                conferir_excel(filtro, 1)

        filtros_sem_resultado = (
            {"motorista_id": self.motoristas[1]},
            {"veiculo_id": 999999},
            {"data_inicio": "2026-11-24"},
            {"data_fim": "2026-11-22"},
        )

        for filtro in filtros_sem_resultado:
            with self.subTest(filtro=filtro):
                conferir_excel(filtro, 0)
