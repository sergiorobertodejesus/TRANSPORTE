from io import BytesIO
from pathlib import Path
from werkzeug.security import generate_password_hash
from ambiente_jornadas import AmbienteJornadas


class TestFotos(AmbienteJornadas):

    def test_inicio_checklist_e_fotografias(self):
        self.encerrar_jornada_padrao()

        db = self.database.conectar()
        try:
            with db:
                cursor = db.execute(
                    "INSERT INTO administradores "
                    "(usuario, senha_hash, ativo) VALUES (?, ?, 1)",
                    (
                        "admin_fotos_teste",
                        generate_password_hash("senha_teste")
                    )
                )
                admin_id = cursor.lastrowid
        finally:
            db.close()

        token = self.acessar_motorista(2)

        checklist ={
        "retrovisores":"sim",
        "farol_alto":"sim",
        "seta_dianteira":"sim",
        "seta_traseira":"sim",
        "luz_freio":"sim",
        "brake_light":"sim",
        "pneus":"sim",
        "avarias_bancos":"nao",
        "avarias_painel":"nao",
        "riscos_portas":"sim",
        "outras_avarias":"nao"
        }

        dados ={
        "acao":"iniciar",
        "csrf_token":token ,
        "km_inicial":"1150",
        "bateria_inicial":"80",
        "descricao_avarias":"Risco na porta"
        }
        dados .update (checklist )

        # Teste de fotografias.
        from PIL import Image

        imagem =BytesIO ()
        Image .new ("RGB",(100 ,100 ),"white").save (
        imagem ,format ="PNG"
        )
        conteudo_foto =imagem .getvalue ()

        arquivos_invalidos =(
        (b"arquivo invalido","teste.txt"),
        (b"imagem corrompida","teste.png"),
        (conteudo_foto ,"teste.jpg"),
        )

        for conteudo ,nome in arquivos_invalidos :
            with self .subTest (arquivo =nome ):
                dados_invalidos =dict (dados )
                dados_invalidos ["foto_km_inicial"]=(
                BytesIO (conteudo ),nome
                )

                resposta =self.cliente .post (
                "/jornada",
                data =dados_invalidos
                )
                self .assertEqual (resposta .status_code ,302 )

                db =self.database .conectar ()
                try :
                    total =db .execute (
                    "SELECT COUNT(*) FROM jornadas "
                    "WHERE motorista_id = ?",
                    (self.motoristas [1 ],)
                    ).fetchone ()[0 ]
                    self .assertEqual (total ,0 )
                finally :
                    db .close ()

                self .assertEqual (
                list (self.modulo_app .PASTA_FOTOS .iterdir ()),
                []
                )

        dados ["foto_km_inicial"]=(
        BytesIO (conteudo_foto ),"teste.png"
        )

        resposta =self.cliente .post ("/jornada",data =dados )
        self .assertEqual (resposta .status_code ,302 )

        with self.cliente .session_transaction ()as sessao :
            mensagens =sessao .get ("_flashes",[])
            self .assertTrue (any (
            "Jornada iniciada e checklist registrado"
            in aviso for _ ,aviso in mensagens
            ))

        db =self.database .conectar ()
        try :
            jornada =db .execute (
            "SELECT * FROM jornadas "
            "WHERE motorista_id = ? "
            "AND status = 'EM_ANDAMENTO'",
            (self.motoristas [1 ],)
            ).fetchone ()

            self .assertIsNotNone (jornada )
            self .assertEqual (
            jornada ["veiculo_id"],self.veiculo_id
            )
            self .assertEqual (jornada ["km_inicial"],1150 )
            self .assertEqual (jornada ["bateria_inicial"],80 )

            registro =db .execute (
            "SELECT * FROM checklists "
            "WHERE jornada_id = ?",
            (jornada ["id"],)
            ).fetchone ()

            self .assertIsNotNone (registro )

            for campo ,valor in checklist .items ():
                self .assertEqual (registro [campo ],valor )

            self .assertEqual (
            registro ["descricao_avarias"],
            "Risco na porta"
            )

            total =db .execute (
            "SELECT COUNT(*) FROM jornadas "
            "WHERE veiculo_id = ? "
            "AND status = 'EM_ANDAMENTO'",
            (self.veiculo_id ,)
            ).fetchone ()[0 ]

            self .assertEqual (total ,1 )
        finally :
            db .close ()


            # Conferencia do armazenamento e acesso.
        nome_foto =jornada ["foto_km_inicial"]
        self .assertTrue (nome_foto )

        caminho =self.modulo_app .PASTA_FOTOS /nome_foto

        self .assertTrue (caminho .is_file ())
        self .assertEqual (
        caminho .read_bytes (),conteudo_foto
        )

        pasta_publica =Path (
        self.modulo_app .app .static_folder
        ).resolve ()

        self .assertNotIn (
        pasta_publica ,caminho .resolve ().parents
        )

        rota_foto ="/foto_jornada/"+nome_foto

        with self.cliente .session_transaction ()as sessao :
            sessao .clear ()

        resposta =self.cliente .get (rota_foto )
        self .assertEqual (resposta .status_code ,302 )

        with self.cliente .session_transaction ()as sessao :
            sessao ["motorista_id"]=self.motoristas [0 ]
            sessao ["nome_motorista"]="Motorista Bloqueio 1"

        resposta =self.cliente .get (rota_foto )
        self .assertIn (resposta .status_code ,(403 ,404 ))

        with self.cliente .session_transaction ()as sessao :
            sessao .clear ()
            sessao ["motorista_id"]=self.motoristas [1 ]
            sessao ["nome_motorista"]="Motorista Bloqueio 2"

        resposta =self.cliente .get (rota_foto )
        self .assertEqual (resposta .status_code ,200 )
        self .assertEqual (resposta .data ,conteudo_foto )
        resposta .close ()

        with self.cliente .session_transaction ()as sessao :
            sessao .clear ()
            sessao ["administrador_id"]=admin_id
            sessao ["nome_administrador"]="Admin Excel Teste"

        resposta =self.cliente .get (rota_foto )
        self .assertEqual (resposta .status_code ,200 )
        self .assertEqual (resposta .data ,conteudo_foto )
        resposta .close ()
