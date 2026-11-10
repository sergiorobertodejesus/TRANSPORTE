import os

from flask_wtf.csrf import CSRFProtect

from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash, abort, send_file
)
from pathlib import Path
from uuid import uuid4
from PIL import Image
from database import conectar, inicializar_banco
from io import BytesIO
from datetime import datetime, date
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

inicializar_banco()

app = Flask(__name__)

# Segurança das sessões e proteção CSRF
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = (
    os.environ.get("FLASK_HTTPS", "0") == "1"
)
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["WTF_CSRF_ENABLED"] = True

app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

# As fotos ficam fora de static, sem acesso público direto.
PASTA_FOTOS = Path(app.instance_path) / "fotos_jornadas"
PASTA_FOTOS.mkdir(parents=True, exist_ok=True)

EXTENSOES_FOTO = {".jpg", ".jpeg", ".png", ".webp"}


def validar_foto(arquivo):
    if not arquivo or not arquivo.filename:
        return None

    extensao = Path(arquivo.filename).suffix.lower()
    formatos = {
        ".jpg": "JPEG",
        ".jpeg": "JPEG",
        ".png": "PNG",
        ".webp": "WEBP",
    }

    if extensao not in formatos:
        raise ValueError("Use uma imagem JPG, PNG ou WEBP.")

    try:
        arquivo.stream.seek(0)
        with Image.open(arquivo.stream) as imagem:
            formato = imagem.format
            largura, altura = imagem.size

            dimensoes_invalidas = (
                largura <= 0
                or altura <= 0
                or largura > 10000
                or altura > 10000
                or largura * altura > 20000000
            )

            if not dimensoes_invalidas:
                imagem.verify()

    except Exception as erro:
        arquivo.stream.seek(0)
        raise ValueError(
            "A imagem está corrompida ou não é válida."
        ) from erro

    if dimensoes_invalidas:
        arquivo.stream.seek(0)
        raise ValueError(
            "A imagem excede o limite de dimensões permitido."
        )

    if formato != formatos[extensao]:
        arquivo.stream.seek(0)
        raise ValueError(
            "A extensão do arquivo não corresponde à imagem."
        )

    try:
        arquivo.stream.seek(0)
        with Image.open(arquivo.stream) as imagem:
            imagem.load()
    except Exception as erro:
        raise ValueError(
            "A imagem está corrompida ou não é válida."
        ) from erro
    finally:
        arquivo.stream.seek(0)

    return extensao


def salvar_foto(arquivo, etapa, extensao):
    if not extensao:
        return None

    nome = f"{uuid4().hex}_{etapa}{extensao}"
    arquivo.save(PASTA_FOTOS / nome)
    return nome


arquivo_chave = Path(__file__).resolve().parent / ".flask_secret_key"
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or arquivo_chave.read_text(encoding="utf-8").strip()

csrf = CSRFProtect(app)


@app.before_request
def validar_sessao_administrador():
    rotas_publicas = {
        "index",
        "login_admin",
        "login_motorista",
        "static",
    }

    if request.endpoint in rotas_publicas:
        return None

    administrador_id = session.get("administrador_id")
    motorista_id = session.get("motorista_id")

    if administrador_id is not None and motorista_id is not None:
        session.clear()
        return redirect(url_for("login_motorista"))

    if administrador_id is None and motorista_id is None:
        return None

    db = conectar()
    try:
        if administrador_id is not None:
            usuario_ativo = db.execute(
                """
                SELECT id
                FROM administradores
                WHERE id = ? AND ativo = 1
                """,
                (administrador_id,)
            ).fetchone()
            destino_login = "login_admin"
        else:
            usuario_ativo = db.execute(
                """
                SELECT m.id
                FROM motoristas m
                JOIN acessos a ON a.motorista_id = m.id
                WHERE m.id = ?
                  AND m.ativo = 1
                  AND a.ativo = 1
                """,
                (motorista_id,)
            ).fetchone()
            destino_login = "login_motorista"
    finally:
        db.close()

    if usuario_ativo is None:
        session.clear()
        return redirect(url_for(destino_login))

    return None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login_motorista", methods=["GET", "POST"])
def login_motorista():
    from werkzeug.security import check_password_hash

    mensagem = ""

    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip().lower()
        senha = request.form.get("senha", "")

        db = conectar()
        try:
            acesso = db.execute("""
                SELECT a.motorista_id, a.usuario, a.senha_hash,
                       m.nome AS nome_motorista
                FROM acessos a
                JOIN motoristas m ON m.id = a.motorista_id
                WHERE a.usuario = ?
                  AND a.ativo = 1
                  AND m.ativo = 1
            """, (usuario,)).fetchone()
        finally:
            db.close()

        if acesso and check_password_hash(acesso["senha_hash"], senha):
            session.clear()
            session["motorista_id"] = acesso["motorista_id"]
            session["nome_motorista"] = acesso["nome_motorista"]
            return redirect(url_for("area_motorista"))

        mensagem = "Usuário ou senha inválidos."

    return render_template(
        "login_motorista.html",
        mensagem=mensagem
    )




@app.route("/login_admin", methods=["GET", "POST"])
def login_admin():
    from werkzeug.security import check_password_hash

    mensagem = ""

    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip().lower()
        senha = request.form.get("senha", "")

        db = conectar()
        try:
            admin = db.execute("""
                SELECT id, usuario, senha_hash
                FROM administradores
                WHERE usuario = ? AND ativo = 1
            """, (usuario,)).fetchone()
        finally:
            db.close()

        if admin and check_password_hash(admin["senha_hash"], senha):
            session.clear()
            session["administrador_id"] = admin["id"]
            session["administrador_usuario"] = admin["usuario"]
            return redirect(url_for("painel_admin"))

        mensagem = "Usuário ou senha inválidos."

    return render_template("login_admin.html", mensagem=mensagem)


@app.route("/sair_admin", methods=["POST"])
def sair_admin():
    if "administrador_id" not in session:
        return redirect(url_for("login_admin"))

    session.clear()
    return redirect(url_for("index"))


def data_valida(valor):
    try:
        data = date.fromisoformat(valor)
        return data.isoformat() == valor
    except (ValueError, TypeError):
        return False

@app.route("/painel_admin")
def painel_admin():
    if "administrador_id" not in session:
        return redirect(url_for("login_admin"))

    motorista_id = request.args.get("motorista_id", "").strip()
    veiculo_id = request.args.get("veiculo_id", "").strip()
    data_inicio = request.args.get("data_inicio", "").strip()
    data_fim = request.args.get("data_fim", "").strip()

    filtros = []
    parametros = []

    if motorista_id.isdigit():
        filtros.append("j.motorista_id = ?")
        parametros.append(int(motorista_id))
    else:
        motorista_id = ""

    if veiculo_id.isdigit():
        filtros.append("j.veiculo_id = ?")
        parametros.append(int(veiculo_id))
    else:
        veiculo_id = ""

    if data_valida(data_inicio):
        filtros.append("substr(j.data_inicio, 1, 10) >= ?")
        parametros.append(data_inicio)
    else:
        data_inicio = ""

    if data_valida(data_fim):
        filtros.append("substr(j.data_inicio, 1, 10) <= ?")
        parametros.append(data_fim)
    else:
        data_fim = ""

    where = ""
    if filtros:
        where = "WHERE " + " AND ".join(filtros)

    db = conectar()
    try:
        em_andamento = db.execute("""
            SELECT COUNT(*) AS total
            FROM jornadas WHERE status = 'EM_ANDAMENTO'
        """).fetchone()["total"]

        encerradas = db.execute("""
            SELECT COUNT(*) AS total
            FROM jornadas WHERE status = 'ENCERRADA'
        """).fetchone()["total"]

        motoristas = db.execute("""
            SELECT
                m.id,
                m.nome,
                m.ativo,
                a.usuario
            FROM motoristas m
            LEFT JOIN acessos a ON a.motorista_id = m.id
            ORDER BY m.nome
        """).fetchall()

        veiculos = db.execute("""
            SELECT id, nome, placa, ativo FROM veiculos
            ORDER BY nome
        """).fetchall()

        escalas = db.execute("""
            SELECT
                e.id,
                e.motorista_id,
                e.veiculo_id,
                e.hora_inicio,
                e.hora_fim,
                m.nome AS motorista,
                v.nome AS veiculo
            FROM escalas e
            JOIN motoristas m ON m.id = e.motorista_id
            JOIN veiculos v ON v.id = e.veiculo_id
            WHERE e.ativo = 1
            ORDER BY m.nome
        """).fetchall()


        where_avarias = ""
        if filtros:
            where_avarias = " AND " + " AND ".join(filtros)

        avarias = db.execute("""
            SELECT
                j.id AS jornada_id,
                j.data_inicio,
                m.nome AS motorista,
                v.nome AS veiculo,
                v.placa AS placa,
                c.descricao_avarias,
                c.foto_avaria
            FROM checklists c
            JOIN jornadas j ON j.id = c.jornada_id
            JOIN motoristas m ON m.id = j.motorista_id
            JOIN veiculos v ON v.id = j.veiculo_id
            WHERE (
                TRIM(COALESCE(c.descricao_avarias, '')) <> ''
                OR COALESCE(c.foto_avaria, '') <> ''
            )
        """ + where_avarias + """
            ORDER BY j.id DESC
        """, parametros).fetchall()

        avarias_jornada = db.execute("""
            SELECT
                j.id AS jornada_id,
                j.data_inicio,
                m.nome AS motorista,
                v.nome AS veiculo,
                v.placa AS placa,
                j.descricao_avaria_final AS descricao_avaria,
                j.foto_avaria_final AS foto_avaria
            FROM jornadas j
            JOIN motoristas m ON m.id = j.motorista_id
            JOIN veiculos v ON v.id = j.veiculo_id
            WHERE (
                TRIM(COALESCE(j.descricao_avaria_final, '')) <> ''
                OR COALESCE(j.foto_avaria_final, '') <> ''
            )
        """ + where_avarias + """
            ORDER BY j.id DESC
        """, parametros).fetchall()

        jornadas = db.execute("""
            SELECT
                j.id,
                m.nome AS motorista,
                v.nome AS veiculo,
                v.placa AS placa,
                j.data_inicio,
                j.data_fim,
                j.km_inicial,
                j.km_final,
                j.foto_km_inicial,
                j.foto_km_final,
                j.status,
                  COALESCE(g.uber_total, 0) AS uber_total,
                  COALESCE(g.noventa_nove_total, 0) AS noventa_nove_total,
                  COALESCE(g.uber_dinheiro, 0) AS uber_dinheiro,
                  COALESCE(g.noventa_nove_dinheiro, 0) AS noventa_nove_dinheiro,
                  COALESCE(g.corridas_particulares, 0) AS corridas_particulares,
                  g.particulares_dinheiro AS particulares_dinheiro,
                  g.uber_pix AS uber_pix,
                  g.noventa_nove_pix AS noventa_nove_pix,
                  g.particulares_pix AS particulares_pix,
                  COALESCE(g.pix_empresa, 0) AS pix_empresa,
                  COALESCE(d.total_despesas, 0) AS total_despesas
            FROM jornadas j
            JOIN motoristas m ON m.id = j.motorista_id
            JOIN veiculos v ON v.id = j.veiculo_id
                LEFT JOIN (
                  SELECT
                      jornada_id,
                      SUM(uber_total) AS uber_total,
                      SUM(noventa_nove_total) AS noventa_nove_total,
                      SUM(uber_dinheiro) AS uber_dinheiro,
                      SUM(noventa_nove_dinheiro) AS noventa_nove_dinheiro,
                      SUM(corridas_particulares) AS corridas_particulares,
                      SUM(particulares_dinheiro) AS particulares_dinheiro,
                      SUM(uber_pix) AS uber_pix,
                      SUM(noventa_nove_pix) AS noventa_nove_pix,
                      SUM(particulares_pix) AS particulares_pix,
                      SUM(pix_empresa) AS pix_empresa
                  FROM ganhos
                  GROUP BY jornada_id
              ) g ON g.jornada_id = j.id
                LEFT JOIN (
                SELECT jornada_id, SUM(valor) AS total_despesas
                FROM despesas
                GROUP BY jornada_id
            ) d ON d.jornada_id = j.id
            """ + where + """
            ORDER BY j.id DESC
        """, parametros).fetchall()
    finally:
        db.close()

    registros = []
    faturamento_total = 0
    despesas_total = 0

    for j in jornadas:
        faturamento = (
            (j["uber_total"] or 0)
            + (j["noventa_nove_total"] or 0)
            + (j["corridas_particulares"] or 0)
        )
        despesas = j["total_despesas"] or 0

        distancia = None
        por_km = None

        if j["km_inicial"] is not None and j["km_final"] is not None:
            distancia = j["km_final"] - j["km_inicial"]
            if distancia > 0:
                por_km = faturamento / distancia

        faturamento_total += faturamento
        despesas_total += despesas

        registros.append({
            "id": j["id"],
            "motorista": j["motorista"],
            "veiculo": j["veiculo"],
            "placa": j["placa"],
            "data_inicio": j["data_inicio"],
            "data_fim": j["data_fim"],
            "foto_km_inicial": j["foto_km_inicial"],
            "foto_km_final": j["foto_km_final"],
            "status": j["status"],
            "uber": j["uber_total"] or 0,
            "noventa_nove": j["noventa_nove_total"] or 0,
            "uber_dinheiro": j["uber_dinheiro"] or 0,
            "noventa_nove_dinheiro": j["noventa_nove_dinheiro"] or 0,
            "corridas_particulares": j["corridas_particulares"] or 0,
            "dinheiro_total": (
                (j["uber_dinheiro"] or 0)
                + (j["noventa_nove_dinheiro"] or 0)
                + (j["particulares_dinheiro"] or 0)
            ),
            "particulares_dinheiro": j["particulares_dinheiro"],
            "uber_pix": j["uber_pix"],
            "noventa_nove_pix": j["noventa_nove_pix"],
            "particulares_pix": j["particulares_pix"],
            "uber_presumido": (
                (j["uber_total"] or 0)
                - (j["uber_dinheiro"] or 0)
                - j["uber_pix"]
                if j["uber_pix"] is not None else None
            ),
            "noventa_nove_presumido": (
                (j["noventa_nove_total"] or 0)
                - (j["noventa_nove_dinheiro"] or 0)
                - j["noventa_nove_pix"]
                if j["noventa_nove_pix"] is not None else None
            ),
            "total_presumido": (
                (j["uber_total"] or 0)
                + (j["noventa_nove_total"] or 0)
                - (j["uber_dinheiro"] or 0)
                - (j["noventa_nove_dinheiro"] or 0)
                - j["uber_pix"]
                - j["noventa_nove_pix"]
                if j["uber_pix"] is not None
                and j["noventa_nove_pix"] is not None
                else None
            ),
            "pix_empresa": j["pix_empresa"] or 0,
            "distancia": distancia,
            "faturamento": faturamento,
            "despesas": despesas,
            "por_km": por_km,
        })

    return render_template(
        "painel_admin.html",
        usuario=session["administrador_usuario"],
        em_andamento=em_andamento,
        encerradas=encerradas,
        jornadas=registros,
        motoristas=motoristas,
        veiculos=veiculos,
        filtro_motorista=motorista_id,
        filtro_veiculo=veiculo_id,
        filtro_data_inicio=data_inicio,
        filtro_data_fim=data_fim,
        escalas=escalas,
        avarias=avarias,
        avarias_jornada=avarias_jornada,
        faturamento_total=faturamento_total,
        despesas_total=despesas_total,
    )
@app.route("/exportar_relatorio_excel")
def exportar_relatorio_excel():
    if "administrador_id" not in session:
        return redirect(url_for("login_admin"))

    motorista_id = request.args.get("motorista_id", "").strip()
    veiculo_id = request.args.get("veiculo_id", "").strip()
    data_inicio = request.args.get("data_inicio", "").strip()
    data_fim = request.args.get("data_fim", "").strip()

    filtros = []
    parametros = []

    if motorista_id.isdigit():
        filtros.append("j.motorista_id = ?")
        parametros.append(int(motorista_id))
    else:
        motorista_id = ""

    if veiculo_id.isdigit():
        filtros.append("j.veiculo_id = ?")
        parametros.append(int(veiculo_id))
    else:
        veiculo_id = ""

    if data_valida(data_inicio):
        filtros.append("substr(j.data_inicio, 1, 10) >= ?")
        parametros.append(data_inicio)
    else:
        data_inicio = ""

    if data_valida(data_fim):
        filtros.append("substr(j.data_inicio, 1, 10) <= ?")
        parametros.append(data_fim)
    else:
        data_fim = ""

    where = ""
    if filtros:
        where = "WHERE " + " AND ".join(filtros)

    db = conectar()

    try:
        jornadas = db.execute("""
            SELECT
                j.id,
                m.nome AS motorista,
                v.nome AS veiculo,
                v.placa,
                j.data_inicio,
                j.data_fim,
                j.km_inicial,
                j.km_final,
                j.bateria_inicial,
                j.bateria_final,
                j.foto_km_inicial,
                j.foto_km_final,
                j.status,
                COALESCE(g.uber_total, 0) AS uber,
                COALESCE(g.noventa_nove_total, 0) AS noventa_nove,
                COALESCE(g.uber_dinheiro, 0) AS uber_dinheiro,
                COALESCE(g.noventa_nove_dinheiro, 0) AS noventa_nove_dinheiro,
                COALESCE(g.corridas_particulares, 0) AS particulares,
                g.particulares_dinheiro AS particulares_dinheiro,
                g.uber_pix AS uber_pix,
                g.noventa_nove_pix AS noventa_nove_pix,
                g.particulares_pix AS particulares_pix,
                COALESCE(g.pix_empresa, 0) AS pix_empresa,
                COALESCE(d.total_despesas, 0) AS despesas
            FROM jornadas j
            JOIN motoristas m ON m.id = j.motorista_id
            JOIN veiculos v ON v.id = j.veiculo_id
            LEFT JOIN (
                SELECT
                    jornada_id,
                    SUM(uber_total) AS uber_total,
                    SUM(noventa_nove_total) AS noventa_nove_total,
                    SUM(uber_dinheiro) AS uber_dinheiro,
                    SUM(noventa_nove_dinheiro) AS noventa_nove_dinheiro,
                    SUM(corridas_particulares) AS corridas_particulares,
                    SUM(particulares_dinheiro) AS particulares_dinheiro,
                    SUM(uber_pix) AS uber_pix,
                    SUM(noventa_nove_pix) AS noventa_nove_pix,
                    SUM(particulares_pix) AS particulares_pix,
                    SUM(pix_empresa) AS pix_empresa
                FROM ganhos
                GROUP BY jornada_id
            ) g ON g.jornada_id = j.id
            LEFT JOIN (
                SELECT jornada_id, SUM(valor) AS total_despesas
                FROM despesas
                GROUP BY jornada_id
            ) d ON d.jornada_id = j.id
            """ + where + """
            ORDER BY j.id DESC
        """, parametros).fetchall()

        ganhos = db.execute("""
            SELECT
                g.id,
                g.jornada_id,
                m.nome AS motorista,
                v.nome AS veiculo,
                g.uber_total,
                g.uber_dinheiro,
                g.noventa_nove_total,
                g.noventa_nove_dinheiro,
                g.corridas_particulares,
                g.particulares_dinheiro,
                g.uber_pix,
                g.noventa_nove_pix,
                g.particulares_pix,
                g.dinheiro_total,
                g.pix_empresa
            FROM ganhos g
            JOIN jornadas j ON j.id = g.jornada_id
            JOIN motoristas m ON m.id = j.motorista_id
            JOIN veiculos v ON v.id = j.veiculo_id
            """ + where + """
            ORDER BY j.id DESC, g.id
        """, parametros).fetchall()

        despesas = db.execute("""
            SELECT
                d.id,
                d.jornada_id,
                j.data_inicio,
                m.nome AS motorista,
                v.nome AS veiculo,
                d.categoria,
                d.valor,
                d.descricao
            FROM despesas d
            JOIN jornadas j ON j.id = d.jornada_id
            JOIN motoristas m ON m.id = j.motorista_id
            JOIN veiculos v ON v.id = j.veiculo_id
            """ + where + """
            ORDER BY j.id DESC, d.id
        """, parametros).fetchall()

        avarias = db.execute("""
            SELECT
                j.id AS jornada_id,
                j.data_inicio,
                m.nome AS motorista,
                v.nome AS veiculo,
                v.placa,
                c.retrovisores,
                c.farol_alto,
                c.seta_dianteira,
                c.seta_traseira,
                c.luz_freio,
                c.brake_light,
                c.pneus,
                c.avarias_bancos,
                c.avarias_painel,
                c.riscos_portas,
                c.outras_avarias,
                c.descricao_avarias,
                c.foto_avaria
            FROM checklists c
            JOIN jornadas j ON j.id = c.jornada_id
            JOIN motoristas m ON m.id = j.motorista_id
            JOIN veiculos v ON v.id = j.veiculo_id
            """ + where + """
            ORDER BY j.id DESC
        """, parametros).fetchall()

    finally:
        db.close()

    arquivo = BytesIO()
    wb = Workbook()

    resumo = wb.active
    resumo.title = "Resumo"

    faturamento_total = sum(
        (j["uber"] or 0) + (j["noventa_nove"] or 0)
        + (j["particulares"] or 0)
        for j in jornadas
    )
    despesas_total = sum(j["despesas"] or 0 for j in jornadas)

    resumo.append(["RELATÓRIO ER TRANSPORTE"])
    resumo.append(["Gerado em", datetime.now().strftime("%d/%m/%Y %H:%M")])
    resumo.append(["Motorista", motorista_id or "Todos"])
    resumo.append(["Veículo", veiculo_id or "Todos"])
    resumo.append(["Data inicial", data_inicio or "Não definida"])
    resumo.append(["Data final", data_fim or "Não definida"])
    resumo.append([])
    resumo.append(["Indicador", "Valor"])
    resumo.append(["Jornadas encontradas", len(jornadas)])
    resumo.append(["Faturamento bruto", faturamento_total])
    resumo.append(["Despesas", despesas_total])
    resumo.append(["Total líquido operacional", faturamento_total - despesas_total])

    aba = wb.create_sheet("Jornadas")
    aba.append([
        "ID", "Motorista", "Veículo", "Placa",
        "Início", "Encerramento", "Status",
        "KM inicial", "KM final", "KM rodados",
        "Bateria inicial", "Bateria final",
        "Uber", "99", "Dinheiro Uber", "Dinheiro 99",
        "Corridas particulares", "Dinheiro particular",
        "Dinheiro total", "PIX Uber", "PIX 99",
        "PIX particulares", "PIX empresa",
        "Uber presumido", "99 presumido", "Total presumido",
        "Faturamento bruto", "Despesas",
        "R$/km", "Foto KM inicial", "Foto KM final"
    ])

    for j in jornadas:
        distancia = None
        if j["km_inicial"] is not None and j["km_final"] is not None:
            distancia = j["km_final"] - j["km_inicial"]

        faturamento = (
            (j["uber"] or 0)
            + (j["noventa_nove"] or 0)
            + (j["particulares"] or 0)
        )
        dinheiro = (
            (j["uber_dinheiro"] or 0)
            + (j["noventa_nove_dinheiro"] or 0)
            + (j["particulares_dinheiro"] or 0)
        )
        por_km = faturamento / distancia if distancia and distancia > 0 else None

        # Converte as datas para o formato reconhecido pelo Excel
        data_inicio = (
            datetime.fromisoformat(j["data_inicio"]).replace(tzinfo=None)
            if j["data_inicio"] else None
        )
        data_fim = (
            datetime.fromisoformat(j["data_fim"]).replace(tzinfo=None)
            if j["data_fim"] else None
        )

        # Indica se existe foto registrada
        foto_inicial = "Sim" if j["foto_km_inicial"] else "Não"
        foto_final = "Sim" if j["foto_km_final"] else "Não"

        aba.append([
            j["id"], j["motorista"], j["veiculo"], j["placa"],
            data_inicio, data_fim, j["status"],
            j["km_inicial"], j["km_final"], distancia,
            j["bateria_inicial"], j["bateria_final"],
            j["uber"], j["noventa_nove"],
            j["uber_dinheiro"], j["noventa_nove_dinheiro"],
            j["particulares"], j["particulares_dinheiro"],
            dinheiro, j["uber_pix"], j["noventa_nove_pix"],
            j["particulares_pix"], j["pix_empresa"],
            (
                (j["uber"] or 0) - (j["uber_dinheiro"] or 0)
                - j["uber_pix"]
                if j["uber_pix"] is not None else None
            ),
            (
                (j["noventa_nove"] or 0)
                - (j["noventa_nove_dinheiro"] or 0)
                - j["noventa_nove_pix"]
                if j["noventa_nove_pix"] is not None else None
            ),
            (
                (j["uber"] or 0) + (j["noventa_nove"] or 0)
                - (j["uber_dinheiro"] or 0)
                - (j["noventa_nove_dinheiro"] or 0)
                - j["uber_pix"] - j["noventa_nove_pix"]
                if j["uber_pix"] is not None
                and j["noventa_nove_pix"] is not None
                else None
            ),
            faturamento, j["despesas"], por_km,
            foto_inicial, foto_final
        ])

    aba = wb.create_sheet("Ganhos")
    aba.append([
        "ID lançamento", "Jornada", "Motorista", "Veículo",
        "Uber", "Dinheiro Uber", "99", "Dinheiro 99",
        "Corridas particulares", "Dinheiro particular",
        "Dinheiro total", "PIX Uber", "PIX 99",
        "PIX particulares", "PIX empresa",
        "Uber presumido", "99 presumido", "Total presumido"
    ])

    for g in ganhos:
        aba.append([
            g["id"], g["jornada_id"], g["motorista"], g["veiculo"],
            g["uber_total"], g["uber_dinheiro"],
            g["noventa_nove_total"], g["noventa_nove_dinheiro"],
            g["corridas_particulares"], g["particulares_dinheiro"],
            g["dinheiro_total"], g["uber_pix"],
            g["noventa_nove_pix"], g["particulares_pix"],
            g["pix_empresa"],
            (
                (g["uber_total"] or 0) - (g["uber_dinheiro"] or 0)
                - g["uber_pix"]
                if g["uber_pix"] is not None else None
            ),
            (
                (g["noventa_nove_total"] or 0)
                - (g["noventa_nove_dinheiro"] or 0)
                - g["noventa_nove_pix"]
                if g["noventa_nove_pix"] is not None else None
            ),
            (
                (g["uber_total"] or 0) + (g["noventa_nove_total"] or 0)
                - (g["uber_dinheiro"] or 0)
                - (g["noventa_nove_dinheiro"] or 0)
                - g["uber_pix"] - g["noventa_nove_pix"]
                if g["uber_pix"] is not None
                and g["noventa_nove_pix"] is not None
                else None
            )
        ])

    aba = wb.create_sheet("Despesas")
    aba.append([
        "ID", "Jornada", "Data", "Motorista",
        "Veículo", "Categoria", "Valor", "Descrição"
    ])

    for d in despesas:
        data_despesa = (
            datetime.fromisoformat(d["data_inicio"]).replace(tzinfo=None)
            if d["data_inicio"] else None
        )

        aba.append([
            d["id"], d["jornada_id"], data_despesa,
            d["motorista"], d["veiculo"],
            d["categoria"], d["valor"], d["descricao"]
        ])

    aba = wb.create_sheet("Avarias")
    aba.append([
        "Jornada", "Data", "Motorista", "Veículo", "Placa",
        "Retrovisores", "Farol alto", "Seta dianteira",
        "Seta traseira", "Luz de freio", "Brake light",
        "Pneus", "Bancos", "Painel", "Riscos nas portas",
        "Outras avarias", "Descrição", "Foto"
    ])

    for a in avarias:
        data_avaria = (
            datetime.fromisoformat(a["data_inicio"]).replace(tzinfo=None)
            if a["data_inicio"] else None
        )

        foto_avaria = "Sim" if a["foto_avaria"] else "Não"

        descricao_avaria = (a["descricao_avarias"] or "").strip()
        if descricao_avaria.lower() in ("<br>", "<br/>", "<br />"):
            descricao_avaria = ""

        aba.append([
            a["jornada_id"], data_avaria, a["motorista"],
            a["veiculo"], a["placa"], a["retrovisores"],
            a["farol_alto"], a["seta_dianteira"],
            a["seta_traseira"], a["luz_freio"],
            a["brake_light"], a["pneus"], a["avarias_bancos"],
            a["avarias_painel"], a["riscos_portas"],
            a["outras_avarias"], descricao_avaria,
            foto_avaria
        ])

    for planilha in wb.worksheets:
        planilha.freeze_panes = "A2"
        planilha.auto_filter.ref = planilha.dimensions

        for celula in planilha[1]:
            celula.font = Font(bold=True, color="FFFFFF")
            celula.fill = PatternFill(
                fill_type="solid", fgColor="153B50"
            )
            celula.alignment = Alignment(
                horizontal="center", vertical="center"
            )

        for coluna in planilha.columns:
            letra = get_column_letter(coluna[0].column)
            maior = max(
                len(str(c.value or "")) for c in coluna
            )
            planilha.column_dimensions[letra].width = min(maior + 3, 35)

        # Quantidade de jornadas: número inteiro, sem moeda
    resumo["B9"].number_format = "0"

    # Indicadores financeiros: formato monetário
    for linha in resumo.iter_rows(min_row=10, max_row=12, min_col=2, max_col=2):
        linha[0].number_format = '"R$" #,##0.00'

        # Formatação específica da aba Jornadas
    planilha = wb["Jornadas"]

    for linha in planilha.iter_rows(min_row=2):
        # ID inteiro
        linha[0].number_format = "0"

        # Datas de início e encerramento
        linha[4].number_format = "dd/mm/yyyy hh:mm"
        linha[5].number_format = "dd/mm/yyyy hh:mm"

        # KM e bateria: números inteiros
        for celula in linha[7:12]:
            if isinstance(celula.value, (int, float)):
                celula.number_format = '#,##0'

        # Valores financeiros: reais
                # Corridas particulares: quantidade inteira
        linha[16].number_format = "0"

        # Valores financeiros: reais
        for celula in linha[12:16]:
            if isinstance(celula.value, (int, float)):
                celula.number_format = '"R$" #,##0.00'

        for celula in linha[17:22]:
            if isinstance(celula.value, (int, float)):
                celula.number_format = '"R$" #,##0.00'

    # Mantém a formatação numérica das outras abas
       # Formatação da aba Ganhos
    planilha = wb["Ganhos"]

    for linha in planilha.iter_rows(min_row=2):
        # IDs inteiros
        linha[0].number_format = "0"
        linha[1].number_format = "0"

        # Valores financeiros em reais
        for indice in [4, 5, 6, 7, 9, 10]:
            if isinstance(linha[indice].value, (int, float)):
                linha[indice].number_format = '"R$" #,##0.00'

        # Corridas particulares: quantidade inteira
        linha[8].number_format = "0"

    # Formatação financeira por nome do cabeçalho
    for nome_aba in ("Jornadas", "Ganhos"):
        planilha = wb[nome_aba]
        for cabecalho in planilha[1]:
            if cabecalho.value in (
                "Uber presumido", "99 presumido", "Total presumido",
                "Faturamento bruto", "Despesas", "R$/km",
                "PIX Uber", "PIX 99", "PIX particulares", "PIX empresa"
            ):
                for coluna in planilha.iter_cols(
                    min_col=cabecalho.column,
                    max_col=cabecalho.column,
                    min_row=2
                ):
                    for celula in coluna:
                        if isinstance(celula.value, (int, float)):
                            celula.number_format = '"R$" #,##0.00'

    # Mantém a formatação numérica da aba Despesas
        # Formatação específica da aba Despesas
    planilha = wb["Despesas"]

    for linha in planilha.iter_rows(min_row=2):
        # IDs inteiros
        linha[0].number_format = "0"
        linha[1].number_format = "0"

        # Data no formato brasileiro
        linha[2].number_format = "dd/mm/yyyy hh:mm"

        # Valor em reais
        if isinstance(linha[6].value, (int, float)):
            linha[6].number_format = '"R$" #,##0.00'
    # Formatação específica da aba Avarias
    planilha = wb["Avarias"]

    for linha in planilha.iter_rows(min_row=2):
        # Jornada: número inteiro
        linha[0].number_format = "0"

        # Data no formato brasileiro
        linha[1].number_format = "dd/mm/yyyy hh:mm"

    wb.save(arquivo)
    arquivo.seek(0)
    nome_arquivo = "relatorio_er_transporte_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".xlsx"

    return send_file(
        arquivo,
        as_attachment=True,
        download_name=nome_arquivo,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.route("/editar_escala", methods=["POST"])
def editar_escala():
    if "administrador_id" not in session:
        return redirect(url_for("login_admin"))

    escala_id = request.form.get("escala_id", "").strip()
    veiculo_id = request.form.get("veiculo_id", "").strip()
    hora_inicio = request.form.get("hora_inicio", "").strip()
    hora_fim = request.form.get("hora_fim", "").strip()

    if not escala_id.isdigit() or not veiculo_id.isdigit():
        flash("Selecione uma escala e um veículo válidos.", "erro")
        return redirect(url_for("painel_admin"))

    import re

    formato_hora = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")

    if not formato_hora.fullmatch(hora_inicio) or not formato_hora.fullmatch(hora_fim):
        flash("Informe horários válidos no formato HH:MM.", "erro")
        return redirect(url_for("painel_admin"))

    db = conectar()
    try:
        escala = db.execute(
            "SELECT id FROM escalas WHERE id = ? AND ativo = 1",
            (int(escala_id),)
        ).fetchone()

        veiculo = db.execute(
            "SELECT id FROM veiculos WHERE id = ? AND ativo = 1",
            (int(veiculo_id),)
        ).fetchone()

        if not escala or not veiculo:
            flash("Escala ou veículo não encontrado ou inativo.", "erro")
            return redirect(url_for("painel_admin"))

        db.execute("""
            UPDATE escalas
            SET veiculo_id = ?, hora_inicio = ?, hora_fim = ?
            WHERE id = ? AND ativo = 1
        """, (int(veiculo_id), hora_inicio, hora_fim, int(escala_id)))

        db.commit()
        flash("Escala atualizada com sucesso.", "sucesso")
    except Exception:
        db.rollback()
        flash("Não foi possível atualizar a escala.", "erro")
    finally:
        db.close()

    return redirect(url_for("painel_admin"))


@app.route("/cadastrar_motorista", methods=["POST"])
def cadastrar_motorista():
    import re
    import sqlite3
    from werkzeug.security import generate_password_hash

    if "administrador_id" not in session:
        return redirect(url_for("login_admin"))

    nome = request.form.get("nome", "").strip()
    usuario = request.form.get("usuario", "").strip().lower()
    senha = request.form.get("senha", "")
    veiculo_id = request.form.get("veiculo_id", "").strip()
    hora_inicio = request.form.get("hora_inicio", "").strip()
    hora_fim = request.form.get("hora_fim", "").strip()

    if len(nome) < 2:
        flash("Informe o nome do motorista.", "erro")
        return redirect(url_for("painel_admin"))

    if not re.fullmatch(r"[a-z0-9._-]{3,30}", usuario):
        flash(
            "O usuário deve ter de 3 a 30 caracteres: "
            "letras minúsculas, números, ponto, hífen ou sublinhado.",
            "erro"
        )
        return redirect(url_for("painel_admin"))

    if len(senha) < 8:
        flash("A senha inicial deve ter pelo menos 8 caracteres.", "erro")
        return redirect(url_for("painel_admin"))

    formato_hora = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")

    if not veiculo_id.isdigit():
        flash("Selecione um veículo válido.", "erro")
        return redirect(url_for("painel_admin"))

    if (
        not formato_hora.fullmatch(hora_inicio)
        or not formato_hora.fullmatch(hora_fim)
    ):
        flash("Informe horários válidos no formato HH:MM.", "erro")
        return redirect(url_for("painel_admin"))

    db = conectar()

    try:
        veiculo = db.execute("""
            SELECT id FROM veiculos
            WHERE id = ? AND ativo = 1
        """, (int(veiculo_id),)).fetchone()

        if not veiculo:
            flash("O veículo selecionado não está ativo.", "erro")
            return redirect(url_for("painel_admin"))

        cursor = db.execute("""
            INSERT INTO motoristas (nome, ativo)
            VALUES (?, 1)
        """, (nome,))

        motorista_id = cursor.lastrowid

        db.execute("""
            INSERT INTO acessos (
                motorista_id, usuario, senha_hash,
                trocar_senha, ativo
            )
            VALUES (?, ?, ?, 1, 1)
        """, (
            motorista_id,
            usuario,
            generate_password_hash(senha)
        ))

        db.execute("""
            INSERT INTO escalas (
                motorista_id, veiculo_id,
                hora_inicio, hora_fim, ativo
            )
            VALUES (?, ?, ?, ?, 1)
        """, (
            motorista_id,
            int(veiculo_id),
            hora_inicio,
            hora_fim
        ))

        db.commit()
        flash(
            "Motorista, acesso e escala cadastrados com sucesso.",
            "sucesso"
        )

    except sqlite3.IntegrityError:
        db.rollback()
        flash(
            "Não foi possível cadastrar. "
            "Confira se o nome ou usuário já existe.",
            "erro"
        )

    except Exception:
        db.rollback()
        app.logger.exception("Erro ao cadastrar motorista")
        flash("Erro ao cadastrar motorista. Consulte o registro do sistema.",
              "erro")

    finally:
        db.close()

    return redirect(url_for("painel_admin"))


@app.route("/motorista")
def area_motorista():
    if "motorista_id" not in session:
        return redirect(url_for("login_motorista"))

    db = conectar()
    try:
        escala = db.execute("""
            SELECT v.nome AS veiculo, v.placa AS placa, e.hora_inicio, e.hora_fim
            FROM escalas e
            JOIN veiculos v ON v.id = e.veiculo_id
            WHERE e.motorista_id = ? AND e.ativo = 1
        """, (session["motorista_id"],)).fetchone()

        jornada_aberta = db.execute("""
            SELECT id, km_inicial, bateria_inicial, data_inicio
            FROM jornadas
            WHERE motorista_id = ? AND status = 'EM_ANDAMENTO'
            ORDER BY id DESC
            LIMIT 1
        """, (session["motorista_id"],)).fetchone()
    finally:
        db.close()

    return render_template(
    "motorista.html",
    nome_motorista=session["nome_motorista"],
    veiculo=escala["veiculo"] if escala else "Escala não definida",
    placa=escala["placa"] if escala else None,
    jornada_aberta=jornada_aberta
)

@app.route("/foto_jornada/<nome_arquivo>")
def foto_jornada(nome_arquivo):
    if Path(nome_arquivo).name != nome_arquivo:
        abort(404)

    administrador_id = session.get("administrador_id")
    motorista_id = session.get("motorista_id")

    # A sessão deve pertencer a apenas um tipo de usuário.
    if administrador_id is not None and motorista_id is not None:
        abort(403)

    if administrador_id is None and motorista_id is None:
        return redirect(url_for("login_motorista"))

    db = conectar()
    try:
        if administrador_id is not None:
            autorizada = db.execute("""
                SELECT 1
                FROM administradores
                WHERE id = ? AND ativo = 1
            """, (administrador_id,)).fetchone()

            if autorizada:
                autorizada = db.execute("""
                    SELECT 1
                    FROM jornadas j
                    WHERE j.foto_km_inicial = ?
                       OR j.foto_km_final = ?
                       OR j.foto_avaria_final = ?
                       OR EXISTS (
                           SELECT 1
                           FROM checklists c
                           WHERE c.jornada_id = j.id
                             AND c.foto_avaria = ?
                       )
                    LIMIT 1
                """, (
                    nome_arquivo,
                    nome_arquivo,
                    nome_arquivo,
                    nome_arquivo
                )).fetchone()
        else:
            autorizada = db.execute("""
                SELECT 1
                FROM motoristas m
                JOIN jornadas j ON j.motorista_id = m.id
                WHERE m.id = ?
                  AND m.ativo = 1
                  AND (
                      j.foto_km_inicial = ?
                      OR j.foto_km_final = ?
                  )
                LIMIT 1
            """, (
                motorista_id,
                nome_arquivo,
                nome_arquivo
            )).fetchone()
    finally:
        db.close()

    caminho = PASTA_FOTOS / nome_arquivo

    if not autorizada or not caminho.is_file():
        abort(404)

    return send_file(caminho, conditional=True)

@app.route("/sair")
def sair():
    session.clear()
    return redirect(url_for("index"))
@app.route("/jornada", methods=["POST"])
def jornada():
    from datetime import datetime, date

    if "motorista_id" not in session:
        return redirect(url_for("login_motorista"))

    motorista_id = session["motorista_id"]
    acao = request.form.get("acao")
    agora = datetime.now().astimezone().isoformat(timespec="seconds")
    db = conectar()
    nome_foto_inicial = None
    nome_foto_final = None
    nome_foto_avaria = None
    nome_foto_avaria_final = None

    try:
        if acao == "iniciar":
            km_texto = request.form.get("km_inicial", "").strip()
            bateria_texto = request.form.get("bateria_inicial", "").strip()

            try:
                km = int(km_texto)
                bateria = int(bateria_texto) if bateria_texto else None
                if km < 0 or (bateria is not None and not 0 <= bateria <= 100):
                    raise ValueError
            except ValueError:
                flash("Confira a quilometragem e a bateria inicial.")
                return redirect(url_for("area_motorista"))

            itens = [
                "retrovisores", "farol_alto", "seta_dianteira",
                "seta_traseira", "luz_freio", "brake_light",
                "pneus", "avarias_bancos", "avarias_painel",
                "riscos_portas", "outras_avarias"
            ]
            respostas = {item: request.form.get(item) for item in itens}

            if any(valor not in ("sim", "nao") for valor in respostas.values()):
                flash("Responda todas as perguntas do checklist.")
                return redirect(url_for("area_motorista"))

            try:
                extensao_foto_inicial = validar_foto(
                    request.files.get("foto_km_inicial")
                )
            except ValueError as erro:
                flash(str(erro))
                return redirect(url_for("area_motorista"))
            try:
                extensao_foto_avaria = validar_foto(
                    request.files.get("foto_avaria")
                )
            except ValueError as erro:
                flash(str(erro))
                return redirect(url_for("area_motorista"))
            with db:
                aberta = db.execute("""
                    SELECT id FROM jornadas
                    WHERE motorista_id = ? AND status = 'EM_ANDAMENTO'
                """, (motorista_id,)).fetchone()

                if aberta:
                    flash("Você já possui uma jornada em andamento.")
                    return redirect(url_for("area_motorista"))

                escalas_ativas = db.execute("""
                    SELECT veiculo_id
                    FROM escalas
                    WHERE motorista_id = ? AND ativo = 1
                """, (motorista_id,)).fetchall()

                if len(escalas_ativas) != 1:
                    flash("Não existe uma escala ativa válida para você.")
                    return redirect(url_for("area_motorista"))

                escala = escalas_ativas[0]





                veiculo_em_uso = db.execute("""
                    SELECT id FROM jornadas
                    WHERE veiculo_id = ?
                      AND status = 'EM_ANDAMENTO'
                """, (escala["veiculo_id"],)).fetchone()

                if veiculo_em_uso:
                    flash("Este veículo já possui uma jornada em andamento.")
                    return redirect(url_for("area_motorista"))
                cursor = db.execute("""
                    INSERT INTO jornadas
                    (motorista_id, veiculo_id, data_inicio, km_inicial,
                     bateria_inicial, status)
                    VALUES (?, ?, ?, ?, ?, 'EM_ANDAMENTO')
                """, (motorista_id, escala["veiculo_id"], agora, km, bateria))

                nome_foto_inicial = salvar_foto(
                    request.files.get("foto_km_inicial"),
                    "inicial",
                    extensao_foto_inicial
                )
                db.execute("""
                    UPDATE jornadas
                    SET foto_km_inicial = ?
                    WHERE id = ?
                """, (nome_foto_inicial, cursor.lastrowid))
                nome_foto_avaria = salvar_foto(
                    request.files.get("foto_avaria"),
                    "avaria",
                    extensao_foto_avaria
                )

                db.execute("""
                    INSERT INTO checklists (
                        jornada_id, retrovisores, farol_alto,
                        seta_dianteira, seta_traseira, luz_freio,
                        brake_light, pneus, avarias_bancos,
                        avarias_painel, riscos_portas,
                        outras_avarias, descricao_avarias, foto_avaria
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    cursor.lastrowid,
                    *(respostas[item] for item in itens),
                    request.form.get("descricao_avarias", "").strip(),
                    nome_foto_avaria
                ))
            flash("Jornada iniciada e checklist registrado.")
            return redirect(url_for("login_motorista"))

        if acao != "encerrar":
            flash("Ação não reconhecida.")
            return redirect(url_for("area_motorista"))

        km_final_texto = request.form.get("km_final", "").strip()
        bateria_texto = request.form.get("bateria_final", "").strip()

        try:
            km_final = int(km_final_texto)
            bateria_final = int(bateria_texto) if bateria_texto else None

            if km_final < 0:
                raise ValueError

            if bateria_final is not None and not 0 <= bateria_final <= 100:
                raise ValueError

        except ValueError:
            flash("Confira a quilometragem e a bateria finais.")
            return redirect(url_for("area_motorista"))

        def ler_valor(campo):
            texto = request.form.get(campo, "").strip()
            valor = float(texto.replace(",", ".")) if texto else 0.0

            if not __import__("math").isfinite(valor) or valor < 0:
                raise ValueError

            return valor

        try:
            uber_total = ler_valor("uber_total")
            uber_dinheiro = ler_valor("uber_dinheiro")
            noventa_nove_total = ler_valor("99_total")
            noventa_nove_dinheiro = ler_valor("99_dinheiro")
            corridas_particulares = ler_valor("corridas_particulares")
            particulares_dinheiro = ler_valor("particulares_dinheiro")
            uber_pix = ler_valor("uber_pix")
            noventa_nove_pix = ler_valor("99_pix")
            particulares_pix = ler_valor("particulares_pix")
            dinheiro_total = (
                uber_dinheiro + noventa_nove_dinheiro
                + particulares_dinheiro
            )
            pix_empresa = ler_valor("pix_empresa")
            recarga = ler_valor("recarga")
            combustivel = ler_valor("combustivel")
            outras_despesas = ler_valor("outras_despesas")
        except ValueError:
            flash("Confira os valores financeiros. Use apenas números não negativos.")
            return redirect(url_for("area_motorista"))

        try:
            extensao_foto_final = validar_foto(
                request.files.get("foto_km_final")
            )
        except ValueError as erro:
            flash(str(erro))
            return redirect(url_for("area_motorista"))

        avaria_final = request.form.get("avaria_final", "").strip().lower()
        descricao_avaria_final = request.form.get("descricao_avaria_final", "").strip()

        if avaria_final not in ("sim", "nao"):
            flash("Informe se identificou alguma avaria durante a jornada.")
            return redirect(url_for("area_motorista"))

        if avaria_final == "sim" and not descricao_avaria_final:
            flash("Descreva a avaria identificada durante a jornada.")
            return redirect(url_for("area_motorista"))

        if avaria_final == "nao":
            descricao_avaria_final = ""

        try:
            extensao_foto_avaria_final = validar_foto(
                request.files.get("foto_avaria_final")
            )
        except ValueError as erro:
            flash(str(erro))
            return redirect(url_for("area_motorista"))

        observacoes = request.form.get("observacoes", "").strip()

        with db:
            aberta = db.execute("""
                SELECT id, km_inicial
                FROM jornadas
                WHERE motorista_id = ? AND status = 'EM_ANDAMENTO'
                ORDER BY id DESC
                LIMIT 1
            """, (motorista_id,)).fetchone()

            if not aberta:
                flash("Não existe jornada aberta para encerrar.")
                return redirect(url_for("area_motorista"))

            if km_final < aberta["km_inicial"]:
                flash("A quilometragem final não pode ser menor que a inicial.")
                return redirect(url_for("area_motorista"))

            jornada_id = aberta["id"]

            nome_foto_final = salvar_foto(
                request.files.get("foto_km_final"),
                "final",
                extensao_foto_final
            )

            nome_foto_avaria_final = salvar_foto(
                request.files.get("foto_avaria_final"),
                "avaria_final",
                extensao_foto_avaria_final
            )

            db.execute("""
                INSERT INTO ganhos (
                    jornada_id, uber_total, uber_dinheiro,
                    noventa_nove_total, noventa_nove_dinheiro,
                    corridas_particulares, dinheiro_total, pix_empresa,
                    particulares_dinheiro, uber_pix,
                    noventa_nove_pix, particulares_pix
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                jornada_id, uber_total, uber_dinheiro,
                noventa_nove_total, noventa_nove_dinheiro,
                corridas_particulares, dinheiro_total, pix_empresa,
                particulares_dinheiro, uber_pix,
                noventa_nove_pix, particulares_pix
            ))

            despesas = [
                ("Recarga elétrica", recarga, observacoes),
                ("Combustível", combustivel, observacoes),
                ("Outras despesas", outras_despesas, observacoes),
            ]

            for categoria, valor, descricao in despesas:
                if valor > 0:
                    db.execute("""
                        INSERT INTO despesas (jornada_id, categoria, valor, descricao)
                        VALUES (?, ?, ?, ?)
                    """, (jornada_id, categoria, valor, descricao))

            db.execute("""
                UPDATE jornadas
                SET data_fim = ?, km_final = ?, bateria_final = ?,
                    foto_km_final = ?, avaria_final = ?,
                    descricao_avaria_final = ?, foto_avaria_final = ?,
                    status = 'ENCERRADA'
                WHERE id = ? AND motorista_id = ?
                  AND status = 'EM_ANDAMENTO'
            """, (
                agora, km_final, bateria_final, nome_foto_final,
                avaria_final, descricao_avaria_final,
                nome_foto_avaria_final, jornada_id, motorista_id
            ))

            if db.execute("SELECT changes()").fetchone()[0] != 1:
                raise RuntimeError(
                    "A jornada não foi encerrada: o registro não foi atualizado."
                )

        flash("Jornada encerrada e dados financeiros registrados.")
        return redirect(url_for("index"))

    except Exception:
        for nome_foto in (
            nome_foto_inicial,
            nome_foto_final,
            nome_foto_avaria,
            nome_foto_avaria_final
        ):
            if nome_foto:
                caminho_foto = PASTA_FOTOS / nome_foto
                try:
                    caminho_foto.unlink(missing_ok=True)
                except OSError:
                    app.logger.exception(
                        "Falha ao remover foto após erro na jornada."
                    )
        raise
    finally:
        db.close()


@app.route("/editar_motorista", methods=["POST"])
def editar_motorista():
    import re
    import sqlite3

    if "administrador_id" not in session:
        return redirect(url_for("login_admin"))

    motorista_id = request.form.get("motorista_id", "").strip()
    nome = request.form.get("nome", "").strip()
    usuario = request.form.get("usuario", "").strip().lower()

    if not motorista_id.isdigit():
        flash("Motorista inválido.", "erro")
        return redirect(url_for("painel_admin"))

    if len(nome) < 2:
        flash("Informe o nome do motorista.", "erro")
        return redirect(url_for("painel_admin"))

    if not re.fullmatch(r"[a-z0-9._-]{3,30}", usuario):
        flash("O usuário deve ter de 3 a 30 caracteres válidos.", "erro")
        return redirect(url_for("painel_admin"))

    db = conectar()

    try:
        motorista = db.execute(
            "SELECT id FROM motoristas WHERE id = ?",
            (int(motorista_id),)
        ).fetchone()

        if not motorista:
            flash("Motorista não encontrado.", "erro")
            return redirect(url_for("painel_admin"))

        duplicado = db.execute("""
            SELECT id FROM motoristas
            WHERE nome = ? AND id != ?
        """, (nome, int(motorista_id))).fetchone()

        if duplicado:
            flash("Já existe um motorista com esse nome.", "erro")
            return redirect(url_for("painel_admin"))

        acesso = db.execute("""
            SELECT id FROM acessos
            WHERE motorista_id = ?
        """, (int(motorista_id),)).fetchone()

        if not acesso:
            flash("O motorista não possui acesso cadastrado.", "erro")
            return redirect(url_for("painel_admin"))

        usuario_duplicado = db.execute("""
            SELECT id FROM acessos
            WHERE usuario = ? AND motorista_id != ?
        """, (usuario, int(motorista_id))).fetchone()

        if usuario_duplicado:
            flash("Esse usuário já pertence a outro motorista.", "erro")
            return redirect(url_for("painel_admin"))

        db.execute("""
            UPDATE motoristas
            SET nome = ?
            WHERE id = ?
        """, (nome, int(motorista_id)))

        db.execute("""
            UPDATE acessos
            SET usuario = ?
            WHERE motorista_id = ?
        """, (usuario, int(motorista_id)))

        db.commit()
        flash("Motorista atualizado com sucesso.", "sucesso")

    except sqlite3.IntegrityError:
        db.rollback()
        flash("Nome ou usuário já cadastrado.", "erro")

    except Exception:
        db.rollback()
        app.logger.exception("Erro ao editar motorista")
        flash("Não foi possível editar o motorista.", "erro")

    finally:
        db.close()

    return redirect(url_for("painel_admin"))


@app.route("/desativar_motorista", methods=["POST"])
def desativar_motorista():
    import sqlite3

    if "administrador_id" not in session:
        return redirect(url_for("login_admin"))

    motorista_id = request.form.get("motorista_id", "").strip()

    if not motorista_id.isdigit():
        flash("Motorista inválido.", "erro")
        return redirect(url_for("painel_admin"))

    db = conectar()

    try:
        motorista = db.execute(
            "SELECT id, nome, ativo FROM motoristas WHERE id = ?",
            (int(motorista_id),)
        ).fetchone()

        if not motorista:
            flash("Motorista não encontrado.", "erro")
            return redirect(url_for("painel_admin"))

        if not motorista["ativo"]:
            flash("Esse motorista já está inativo.", "erro")
            return redirect(url_for("painel_admin"))

        jornada = db.execute("""
            SELECT id FROM jornadas
            WHERE motorista_id = ?
              AND status = 'EM_ANDAMENTO'
            LIMIT 1
        """, (int(motorista_id),)).fetchone()

        if jornada:
            flash(
                "Não é possível desativar: o motorista tem uma jornada em andamento.",
                "erro"
            )
            return redirect(url_for("painel_admin"))

        db.execute(
            "UPDATE motoristas SET ativo = 0 WHERE id = ?",
            (int(motorista_id),)
        )
        db.execute(
            "UPDATE acessos SET ativo = 0 WHERE motorista_id = ?",
            (int(motorista_id),)
        )
        db.execute(
            "UPDATE escalas SET ativo = 0 WHERE motorista_id = ?",
            (int(motorista_id),)
        )

        db.commit()
        flash("Motorista desativado. O histórico foi preservado.", "sucesso")

    except sqlite3.Error:
        db.rollback()
        app.logger.exception("Erro ao desativar motorista")
        flash("Não foi possível desativar o motorista.", "erro")

    finally:
        db.close()

    return redirect(url_for("painel_admin"))

@app.route("/cadastrar_veiculo", methods=["POST"])
def cadastrar_veiculo():
    import re
    import sqlite3

    if "administrador_id" not in session:
        return redirect(url_for("login_admin"))

    nome = request.form.get("nome", "").strip()
    placa_digitada = request.form.get("placa", "").strip()
    placa = re.sub(r"[^A-Za-z0-9]", "", placa_digitada).upper()

    if len(nome) < 2 or len(nome) > 50:
        flash("O nome do veículo deve ter entre 2 e 50 caracteres.", "erro")
        return redirect(url_for("painel_admin"))

    if placa and not re.fullmatch(
        r"[A-Z]{3}[0-9][A-Z0-9][0-9]{2}", placa
    ):
        flash(
            "Informe uma placa válida, como ABC1234 ou ABC1D23.",
            "erro"
        )
        return redirect(url_for("painel_admin"))

    db = conectar()

    try:
        nome_existente = db.execute("""
            SELECT id FROM veiculos
            WHERE LOWER(nome) = LOWER(?)
        """, (nome,)).fetchone()

        if nome_existente:
            flash("Já existe um veículo com esse nome.", "erro")
            return redirect(url_for("painel_admin"))

        if placa:
            placa_existente = db.execute("""
                SELECT id FROM veiculos
                WHERE UPPER(REPLACE(REPLACE(placa, '-', ''), ' ', '')) = ?
            """, (placa,)).fetchone()

            if placa_existente:
                flash("Essa placa já está cadastrada.", "erro")
                return redirect(url_for("painel_admin"))

        db.execute("""
            INSERT INTO veiculos (nome, placa, ativo)
            VALUES (?, ?, 1)
        """, (nome, placa or None))

        db.commit()
        flash("Veículo cadastrado com sucesso.", "sucesso")

    except sqlite3.Error:
        db.rollback()
        app.logger.exception("Erro ao cadastrar veículo")
        flash("Não foi possível cadastrar o veículo.", "erro")

    finally:
        db.close()

    return redirect(url_for("painel_admin"))



@app.route("/editar_veiculo", methods=["POST"])
def editar_veiculo():
    import re
    import sqlite3

    if "administrador_id" not in session:
        return redirect(url_for("login_admin"))

    veiculo_id = request.form.get("veiculo_id", "").strip()
    placa_digitada = request.form.get("placa", "").strip()
    placa = re.sub(r"[^A-Za-z0-9]", "", placa_digitada).upper()

    if not veiculo_id.isdigit():
        flash("Veículo inválido.", "erro")
        return redirect(url_for("painel_admin"))

    if placa and not re.fullmatch(
        r"[A-Z]{3}[0-9][A-Z0-9][0-9]{2}", placa
    ):
        flash("Informe uma placa válida.", "erro")
        return redirect(url_for("painel_admin"))

    db = conectar()

    try:
        veiculo = db.execute(
            "SELECT id FROM veiculos WHERE id = ?",
            (int(veiculo_id),)
        ).fetchone()

        if not veiculo:
            flash("Veículo não encontrado.", "erro")
            return redirect(url_for("painel_admin"))

        if placa:
            placa_existente = db.execute("""
                SELECT id FROM veiculos
                WHERE UPPER(REPLACE(REPLACE(placa, '-', ''), ' ', '')) = ?
                  AND id != ?
            """, (placa, int(veiculo_id))).fetchone()

            if placa_existente:
                flash("Essa placa já pertence a outro veículo.", "erro")
                return redirect(url_for("painel_admin"))

        db.execute(
            "UPDATE veiculos SET placa = ? WHERE id = ?",
            (placa or None, int(veiculo_id))
        )

        db.commit()
        flash("Placa atualizada com sucesso.", "sucesso")

    except sqlite3.Error:
        db.rollback()
        app.logger.exception("Erro ao editar placa do veículo")
        flash("Não foi possível atualizar a placa.", "erro")

    finally:
        db.close()

    return redirect(url_for("painel_admin"))

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")