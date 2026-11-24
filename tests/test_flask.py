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


    def test_veiculo_ocupado(self):
        self.assertEqual(os.environ.get("ER_AMBIENTE"), "teste")

        import database
        from flask import Flask

        with tempfile.TemporaryDirectory() as pasta:
            banco = Path(pasta) / "jornadas.db"

            with patch.object(database, "DB_PATH", banco):
                with patch.dict(os.environ, {
                    "FLASK_SECRET_KEY": "chave-exclusiva-testes"
                }):
                    flask_original = Flask

                    def flask_temporario(*args, **kwargs):
                        kwargs["instance_path"] = str(
                            Path(pasta) / "instance"
                        )
                        return flask_original(*args, **kwargs)

                    with patch("flask.Flask", flask_temporario):
                        with patch.dict(sys.modules, {"app": None}):
                            sys.modules.pop("app", None)
                            import app as modulo_app

                    try:
                        db = database.conectar()
                        try:
                            cursor = db.execute(
                                "INSERT INTO veiculos (nome, ativo) "
                                "VALUES ('Veiculo Bloqueio Teste', 1)"
                            )
                            veiculo_id = cursor.lastrowid
                            motoristas = []

                            for numero in (1, 2):
                                cursor = db.execute(
                                    "INSERT INTO motoristas (nome, ativo) "
                                    "VALUES (?, 1)",
                                    (f"Motorista Bloqueio {numero}",)
                                )
                                motorista_id = cursor.lastrowid
                                motoristas.append(motorista_id)

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
                                    (motorista_id, veiculo_id)
                                )

                            db.execute(
                                "INSERT INTO jornadas "
                                "(motorista_id, veiculo_id, "
                                "data_inicio, km_inicial, status) "
                                "VALUES (?, ?, '2026-11-23T08:00:00', "
                                "1000, 'EM_ANDAMENTO')",
                                (motoristas[0], veiculo_id)
                            )
                            db.commit()
                        finally:
                            db.close()

                        cliente = modulo_app.app.test_client()

                        with cliente.session_transaction() as sessao:
                            sessao["motorista_id"] = motoristas[1]
                            sessao["nome_motorista"] = "Motorista Bloqueio 2"

                        pagina = cliente.get("/motorista")
                        self.assertEqual(pagina.status_code, 200)
                        token = extrair_csrf(pagina.data)

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

                        resposta = cliente.post(
                            "/jornada",
                            data=dados,
                            follow_redirects=False
                        )
                        self.assertEqual(resposta.status_code, 302)

                        with cliente.session_transaction() as sessao:
                            mensagens = sessao.get("_flashes", [])
                            self.assertTrue(any(
                                "veículo já possui uma jornada"
                                in mensagem
                                for _, mensagem in mensagens
                            ))

                        db = database.conectar()
                        try:
                            jornadas = db.execute(
                                "SELECT motorista_id, status "
                                "FROM jornadas ORDER BY id"
                            ).fetchall()
                            self.assertEqual(len(jornadas), 1)
                            self.assertEqual(
                                jornadas[0]["motorista_id"], motoristas[0]
                            )
                            self.assertEqual(
                                jornadas[0]["status"], "EM_ANDAMENTO"
                            )

                        finally:
                            db.close()

                        # Teste de encerramento financeiro.
                        with cliente.session_transaction() as sessao:
                            sessao.clear()
                            sessao["motorista_id"] = motoristas[0]
                            sessao["nome_motorista"] = "Motorista Bloqueio 1"

                        pagina = cliente.get("/motorista")
                        self.assertEqual(pagina.status_code, 200)
                        token = extrair_csrf(pagina.data)


                        # Teste de encerramentos invalidos.
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

                                resposta = cliente.post(
                                    "/jornada", data=dados
                                )

                                self.assertEqual(
                                    resposta.status_code, 302
                                )

                                with cliente.session_transaction() as sessao:
                                    mensagens = sessao.pop("_flashes", [])
                                    self.assertTrue(any(
                                        mensagem in aviso
                                        for _, aviso in mensagens
                                    ))

                                db = database.conectar()
                                try:
                                    jornada = db.execute(
                                        "SELECT id, status FROM jornadas "
                                        "WHERE motorista_id = ?",
                                        (motoristas[0],)
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

                        resposta = cliente.post("/jornada", data={
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

                        db = database.conectar()
                        try:
                            jornada = db.execute(
                                "SELECT status, km_inicial, km_final "
                                "FROM jornadas WHERE motorista_id = ?",
                                (motoristas[0],)
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
                                (motoristas[0],)
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
                                (motoristas[0],)
                            ).fetchone()

                            self.assertAlmostEqual(
                                despesas["total"], 70
                            )
                        finally:
                            db.close()

                        # Teste de exportacao Excel.
                        from io import BytesIO
                        from openpyxl import load_workbook
                        from werkzeug.security import generate_password_hash

                        rota = "/exportar_relatorio_excel"

                        with cliente.session_transaction() as sessao:
                            sessao.clear()

                        resposta = cliente.get(rota)
                        self.assertEqual(resposta.status_code, 302)

                        with cliente.session_transaction() as sessao:
                            sessao["motorista_id"] = motoristas[0]
                            sessao["nome_motorista"] = "Motorista Bloqueio 1"

                        resposta = cliente.get(rota)
                        self.assertEqual(resposta.status_code, 302)

                        db = database.conectar()
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

                        with cliente.session_transaction() as sessao:
                            sessao.clear()
                            sessao["administrador_id"] = admin_id
                            sessao["nome_administrador"] = "Admin Excel Teste"

                        def conferir_excel(filtros, quantidade):
                            resposta = cliente.get(
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
                            {"motorista_id": motoristas[0]},
                            {"veiculo_id": veiculo_id},
                            {"data_inicio": "2026-11-23"},
                            {"data_fim": "2026-11-23"},
                        )

                        for filtro in filtros_validos:
                            with self.subTest(filtro=filtro):
                                conferir_excel(filtro, 1)

                        filtros_sem_resultado = (
                            {"motorista_id": motoristas[1]},
                            {"veiculo_id": 999999},
                            {"data_inicio": "2026-11-24"},
                            {"data_fim": "2026-11-22"},
                        )

                        for filtro in filtros_sem_resultado:
                            with self.subTest(filtro=filtro):
                                conferir_excel(filtro, 0)

                    finally:
                        sys.modules.pop("app", None)


if __name__ == "__main__":
    unittest.main()
