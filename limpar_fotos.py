#!/usr/bin/env python3
"""Limpeza segura das fotografias da ER Transporte."""

import argparse
import fcntl
import os
import sqlite3
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from database import conectar, DB_PATH

RETENCAO_DIAS = 14

BASE = Path(__file__).resolve().parent
PASTA_FOTOS = BASE / "instance" / "fotos_jornadas"
PASTA_QUARENTENA = BASE / "instance" / "quarentena_fotos"
ARQUIVO_LOCK = BASE / "instance" / ".limpeza_fotos.lock"

CAMPOS = (
    ("jornadas", "foto_km_inicial"),
    ("jornadas", "foto_km_final"),
    ("jornadas", "foto_avaria_final"),
    ("checklists", "foto_avaria"),
)


def data_utc(valor):
    if not valor:
        return None
    data = datetime.fromisoformat(valor)
    if data.tzinfo is None:
        raise ValueError(f"Data sem fuso horário: {valor}")
    return data.astimezone(timezone.utc)


def nome_seguro(nome):
    return (
        isinstance(nome, str)
        and nome not in ("", ".", "..")
        and Path(nome).name == nome
        and "/" not in nome
        and "\\" not in nome
    )


@contextmanager
def bloqueio():
    ARQUIVO_LOCK.parent.mkdir(parents=True, exist_ok=True)
    with ARQUIVO_LOCK.open("a+b") as arquivo:
        fcntl.flock(arquivo.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(arquivo.fileno(), fcntl.LOCK_UN)


def referencias_atuais(db):
    referencias = set()
    for tabela, campo in CAMPOS:
        linhas = db.execute(
            f"SELECT {campo} FROM {tabela} "
            f"WHERE {campo} IS NOT NULL"
        )
        referencias.update(r[0] for r in linhas)
    return referencias


def recuperar(db):
    """Reconcilia quarentena com o estado confirmado no SQLite."""
    if not PASTA_QUARENTENA.exists():
        return

    if PASTA_QUARENTENA.is_symlink():
        raise RuntimeError("Pasta de quarentena é link simbólico.")

    referencias = referencias_atuais(db)

    for origem in sorted(PASTA_QUARENTENA.iterdir()):
        nome = origem.name

        if not nome_seguro(nome) or origem.is_symlink():
            raise RuntimeError(
                f"Entrada insegura na quarentena: {nome}"
            )

        if not origem.is_file():
            raise RuntimeError(
                f"Entrada inesperada na quarentena: {nome}"
            )

        destino = PASTA_FOTOS / nome

        if nome in referencias:
            if destino.exists() or destino.is_symlink():
                raise RuntimeError(
                    f"Conflito ao restaurar fotografia: {nome}"
                )
            origem.rename(destino)
            print("[RECUPERADA]", nome)
        else:
            origem.unlink()
            print("[EXCLUSÃO CONCLUÍDA]", nome)


def selecionar_candidatos(db, limite):
    registros = db.execute("""
        SELECT
            j.id,
            j.status,
            j.data_fim,
            j.foto_km_inicial,
            j.foto_km_final,
            j.foto_avaria_final,
            c.foto_avaria AS foto_avaria_inicial
        FROM jornadas j
        LEFT JOIN checklists c ON c.jornada_id = j.id
    """).fetchall()

    referencias = defaultdict(list)

    for registro in registros:
        encerramento = data_utc(registro["data_fim"])

        elegivel = (
            registro["status"] == "ENCERRADA"
            and encerramento is not None
            and encerramento <= limite
        )

        for campo in (
            "foto_km_inicial",
            "foto_km_final",
            "foto_avaria_final",
            "foto_avaria_inicial",
        ):
            nome = registro[campo]
            if nome:
                referencias[nome].append(elegivel)

    candidatos = []

    for nome, situacoes in sorted(referencias.items()):
        if not all(situacoes):
            continue

        if not nome_seguro(nome):
            print("[IGNORADO: NOME INVÁLIDO]", nome)
            continue

        caminho = PASTA_FOTOS / nome

        if caminho.is_symlink():
            print("[IGNORADO: LINK SIMBÓLICO]", nome)
            continue

        if caminho.exists() and not caminho.is_file():
            print("[IGNORADO: NÃO É ARQUIVO]", nome)
            continue

        tamanho = caminho.stat().st_size if caminho.is_file() else 0
        candidatos.append((nome, caminho, tamanho))

        print(
            "[ELEGÍVEL]",
            nome,
            f"({tamanho / 1024 / 1024:.2f} MB)"
        )

    return registros, candidatos


def executar(aplicar=False, agora=None):
    ambiente = os.environ.get("ER_AMBIENTE", "").strip().lower()

    if ambiente not in ("teste", "producao"):
        raise SystemExit(
            "Informe ER_AMBIENTE=teste ou ER_AMBIENTE=producao."
        )

    if not DB_PATH.is_file():
        raise SystemExit("Banco de dados não encontrado.")

    if not PASTA_FOTOS.is_dir() or PASTA_FOTOS.is_symlink():
        raise SystemExit("Pasta de fotografias inválida.")

    agora = agora or datetime.now(timezone.utc)
    limite = agora - timedelta(days=RETENCAO_DIAS)

    print("===== LIMPEZA DE FOTOGRAFIAS =====")
    print("Ambiente:", ambiente)
    print("Modo:", "EXECUÇÃO" if aplicar else "SIMULAÇÃO")
    print("Banco:", DB_PATH)
    print("Limite UTC:", limite.isoformat())

    with bloqueio():
        db = conectar()

        try:
            if aplicar:
                db.execute("BEGIN IMMEDIATE")
                recuperar(db)
            else:
                db.execute("BEGIN")

                if PASTA_QUARENTENA.exists():
                    pendentes = list(PASTA_QUARENTENA.iterdir())
                    if pendentes:
                        print(
                            "[AVISO] Há arquivos aguardando "
                            "recuperação na quarentena:",
                            len(pendentes)
                        )

            registros, candidatos = selecionar_candidatos(db, limite)

            print("\n===== RESUMO =====")
            print("Registros consultados:", len(registros))
            print("Fotografias elegíveis:", len(candidatos))
            print(
                "Espaço potencial:",
                f"{sum(c[2] for c in candidatos) / 1024 / 1024:.2f} MB"
            )

            if not aplicar:
                db.rollback()
                print("Nenhuma alteração realizada.")
                return

            PASTA_QUARENTENA.mkdir(parents=True, exist_ok=True)

            movimentados = []

            try:
                for nome, origem, _ in candidatos:
                    destino = PASTA_QUARENTENA / nome

                    if destino.exists() or destino.is_symlink():
                        raise RuntimeError(
                            f"Conflito na quarentena: {nome}"
                        )

                    if origem.is_file():
                        origem.rename(destino)
                        movimentados.append(nome)
                        print("[QUARENTENA]", nome)

                for nome, _, _ in candidatos:
                    for tabela, campo in CAMPOS:
                        db.execute(
                            f"UPDATE {tabela} SET {campo} = NULL "
                            f"WHERE {campo} = ?",
                            (nome,)
                        )

                db.commit()

            except Exception:
                db.rollback()

                # Restauração após falha controlada.
                # Em caso de interrupção abrupta, a próxima
                # execução fará a recuperação pelo SQLite.
                recuperar(db)
                raise

            # O banco já confirmou a remoção das referências.
            # Arquivos restantes serão reconciliados na
            # próxima execução caso haja interrupção aqui.
            recuperar(db)

            print("\n===== RESULTADO =====")
            print("Fotografias processadas:", len(candidatos))
            print("Limpeza concluída.")

        finally:
            db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--executar",
        action="store_true",
        help="Executa a limpeza das fotografias elegíveis"
    )

    parser.add_argument(
        "--data-simulada",
        help="Data UTC para simulação, formato AAAA-MM-DD"
    )

    args = parser.parse_args()

    if args.data_simulada and (
        args.executar
        or os.environ.get("ER_AMBIENTE") != "teste"
    ):
        parser.error(
            "--data-simulada somente em simulação no ambiente teste"
        )

    agora = None

    if args.data_simulada:
        agora = datetime.fromisoformat(
            args.data_simulada
        ).replace(tzinfo=timezone.utc)

    executar(aplicar=args.executar, agora=agora)
