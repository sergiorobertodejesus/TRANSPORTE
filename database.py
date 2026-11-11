
import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

AMBIENTE = os.getenv("ER_AMBIENTE", "producao").strip().lower()

if AMBIENTE not in ("producao", "teste"):
    raise ValueError("ER_AMBIENTE deve ser 'producao' ou 'teste'.")

NOME_BANCO = (
    "transporte_teste.db"
    if AMBIENTE == "teste"
    else "transporte.db"
)

DB_PATH = BASE_DIR / NOME_BANCO


def conectar():
    conexao = sqlite3.connect(DB_PATH, timeout=10)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    conexao.execute("PRAGMA busy_timeout = 10000")
    return conexao


def inicializar_banco():
    with conectar() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS administradores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL UNIQUE,
                senha_hash TEXT NOT NULL,
                ativo INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS motoristas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                ativo INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS veiculos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                placa TEXT,
                ativo INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS acessos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                motorista_id INTEGER NOT NULL UNIQUE,
                usuario TEXT NOT NULL UNIQUE,
                senha_hash TEXT NOT NULL,
                trocar_senha INTEGER NOT NULL DEFAULT 1,
                ativo INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (motorista_id) REFERENCES motoristas(id)
            );

            CREATE TABLE IF NOT EXISTS escalas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                motorista_id INTEGER NOT NULL,
                veiculo_id INTEGER NOT NULL,
                hora_inicio TEXT NOT NULL,
                hora_fim TEXT NOT NULL,
                ativo INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (motorista_id) REFERENCES motoristas(id),
                FOREIGN KEY (veiculo_id) REFERENCES veiculos(id)
            );

            CREATE TABLE IF NOT EXISTS jornadas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                motorista_id INTEGER NOT NULL,
                veiculo_id INTEGER NOT NULL,
                data_inicio TEXT NOT NULL,
                km_inicial INTEGER,
                bateria_inicial INTEGER,
                data_fim TEXT,
                km_final INTEGER,
                bateria_final INTEGER,
                status TEXT NOT NULL DEFAULT 'EM_ANDAMENTO',
                FOREIGN KEY (motorista_id) REFERENCES motoristas(id),
                FOREIGN KEY (veiculo_id) REFERENCES veiculos(id)
            );

            CREATE TABLE IF NOT EXISTS checklists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jornada_id INTEGER NOT NULL UNIQUE,
                retrovisores TEXT NOT NULL,
                farol_alto TEXT NOT NULL,
                seta_dianteira TEXT NOT NULL,
                seta_traseira TEXT NOT NULL,
                luz_freio TEXT NOT NULL,
                brake_light TEXT NOT NULL,
                pneus TEXT NOT NULL,
                avarias_bancos TEXT NOT NULL,
                avarias_painel TEXT NOT NULL,
                riscos_portas TEXT NOT NULL,
                outras_avarias TEXT NOT NULL,
                descricao_avarias TEXT,
                foto_avaria TEXT,
                FOREIGN KEY (jornada_id) REFERENCES jornadas(id)
            );

            CREATE TABLE IF NOT EXISTS ganhos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jornada_id INTEGER NOT NULL UNIQUE,
                uber_total REAL NOT NULL DEFAULT 0,
                uber_dinheiro REAL NOT NULL DEFAULT 0,
                noventa_nove_total REAL NOT NULL DEFAULT 0,
                noventa_nove_dinheiro REAL NOT NULL DEFAULT 0,
                corridas_particulares REAL NOT NULL DEFAULT 0,
                dinheiro_total REAL NOT NULL DEFAULT 0,
                FOREIGN KEY (jornada_id) REFERENCES jornadas(id)
            );

            CREATE TABLE IF NOT EXISTS despesas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jornada_id INTEGER NOT NULL,
                categoria TEXT NOT NULL,
                valor REAL NOT NULL DEFAULT 0,
                descricao TEXT,
                FOREIGN KEY (jornada_id) REFERENCES jornadas(id)
            );
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS auditoria_jornadas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jornada_id INTEGER NOT NULL,
                administrador_id INTEGER NOT NULL,
                data_alteracao TEXT NOT NULL,
                motivo TEXT NOT NULL,
                dados_anteriores TEXT NOT NULL,
                dados_novos TEXT NOT NULL,
                FOREIGN KEY (jornada_id) REFERENCES jornadas(id),
                FOREIGN KEY (administrador_id) REFERENCES administradores(id)
            )
        """)

        # Migrações dos campos adicionais.
        colunas_jornadas = {
            linha["name"]
            for linha in db.execute("PRAGMA table_info(jornadas)")
        }

        colunas_ganhos = {
            linha["name"]
            for linha in db.execute("PRAGMA table_info(ganhos)")
        }

        colunas_checklists = {
            linha["name"]
            for linha in db.execute("PRAGMA table_info(checklists)")
        }

        # Campos financeiros adicionais.
        for campo in (
            "particulares_dinheiro",
            "uber_pix",
            "noventa_nove_pix",
            "particulares_pix",
        ):
            if campo not in colunas_ganhos:
                db.execute(
                    f"ALTER TABLE ganhos ADD COLUMN {campo} REAL"
                )

        if "pix_empresa" not in colunas_ganhos:
            db.execute("""
                ALTER TABLE ganhos
                ADD COLUMN pix_empresa REAL NOT NULL DEFAULT 0
            """)

        if "foto_km_inicial" not in colunas_jornadas:
            db.execute("""
                ALTER TABLE jornadas
                ADD COLUMN foto_km_inicial TEXT
            """)

        if "foto_km_final" not in colunas_jornadas:
            db.execute("""
                ALTER TABLE jornadas
                ADD COLUMN foto_km_final TEXT
            """)

        if "avaria_final" not in colunas_jornadas:
            db.execute("""
                ALTER TABLE jornadas
                ADD COLUMN avaria_final TEXT
            """)

        if "descricao_avaria_final" not in colunas_jornadas:
            db.execute("""
                ALTER TABLE jornadas
                ADD COLUMN descricao_avaria_final TEXT
            """)

        if "foto_avaria_final" not in colunas_jornadas:
            db.execute("""
                ALTER TABLE jornadas
                ADD COLUMN foto_avaria_final TEXT
            """)

        if "foto_avaria" not in colunas_checklists:
            db.execute("""
                ALTER TABLE checklists
                ADD COLUMN foto_avaria TEXT
            """)

        # Migração da tabela escalas para permitir histórico.
        sql_escalas = db.execute("""
            SELECT sql
            FROM sqlite_master
            WHERE type = 'table' AND name = 'escalas'
        """).fetchone()["sql"]

        if "UNIQUE" in sql_escalas.upper():
            db.execute("""
                CREATE TABLE escalas_nova (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    motorista_id INTEGER NOT NULL,
                    veiculo_id INTEGER NOT NULL,
                    hora_inicio TEXT NOT NULL,
                    hora_fim TEXT NOT NULL,
                    ativo INTEGER NOT NULL DEFAULT 1,
                    FOREIGN KEY (motorista_id) REFERENCES motoristas(id),
                    FOREIGN KEY (veiculo_id) REFERENCES veiculos(id)
                )
            """)

            db.execute("""
                INSERT INTO escalas_nova (
                    id, motorista_id, veiculo_id,
                    hora_inicio, hora_fim, ativo
                )
                SELECT
                    id, motorista_id, veiculo_id,
                    hora_inicio, hora_fim, ativo
                FROM escalas
            """)

            db.execute("DROP TABLE escalas")
            db.execute("ALTER TABLE escalas_nova RENAME TO escalas")

        # Uma única escala ativa por motorista.
        db.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_escalas_motorista_ativo
            ON escalas (motorista_id)
            WHERE ativo = 1
        """)
        # Índice para agilizar consultas de jornadas por motorista.
        db.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_jornadas_motorista_id
            ON jornadas (motorista_id)
        """)
        # Índice para agilizar consultas e agrupamentos de despesas por jornada.
        db.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_despesas_jornada_id
            ON despesas (jornada_id)
        """)
        # Cadastros básicos de veículos.
        nomes_veiculos = [
            "GS",
            "Song",
            "Mini preto",
            "Mini branco",
            "Polo"
        ]

        for nome in nomes_veiculos:
            db.execute(
                "INSERT OR IGNORE INTO veiculos (nome) VALUES (?)",
                (nome,)
            )

        # Cadastros iniciais de motoristas.
        nomes_motoristas = [
            "Pedro",
            "Joe",
            "Gilmario",
            "Gerson",
            "Cristiano",
            "Henrique",
            "Sergio",
            "Pacson",
            "Kleberson",
            "Wagner"
        ]

        for nome in nomes_motoristas:
            db.execute(
                "INSERT OR IGNORE INTO motoristas (nome) VALUES (?)",
                (nome,)
            )

    print(f"Banco inicializado: {DB_PATH}")


if __name__ == "__main__":
    inicializar_banco()
