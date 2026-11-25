import argparse
import logging
import os
import sqlite3
import tempfile

from datetime import datetime, timedelta, time
from pathlib import Path
from zoneinfo import ZoneInfo

from consulta_jornadas import consultar_jornadas
from relatorio_financeiro import consolidar_financeiro
from relatorio_produtividade import consolidar_produtividade
from excel_financeiro import gerar_excel_financeiro
from excel_produtividade import gerar_excel_produtividade
from pdf_executivo import gerar_pdf_executivo
from periodo_operacional import limites_operacionais


FUSO = ZoneInfo("America/Sao_Paulo")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

log = logging.getLogger("relatorio_diario")


def data_referencia(agora=None):
    agora = agora or datetime.now(FUSO)
    agora = agora.astimezone(FUSO)

    dias = 1 if agora.time() >= time(7) else 2

    return (
        agora.date() - timedelta(days=dias)
    ).isoformat()


def validar(financeiro, produtividade, jornadas):
    f = financeiro["geral"]
    p = produtividade["geral"]

    if not f["jornadas"] == p["jornadas"] == len(jornadas):
        raise ValueError("Quantidade de jornadas divergente.")

    if f["bruto"] != p["bruto"]:
        raise ValueError("Faturamento bruto divergente.")

    if f["liquido"] != f["bruto"] - f["despesas"]:
        raise ValueError("Liquido operacional inconsistente.")

    if f["despesas"] != (
        f["recarga"]
        + f["combustivel"]
        + f["outras_despesas"]
    ):
        raise ValueError("Despesas inconsistentes.")

    for grupo in ("motoristas", "veiculos"):
        for campo in (
            "jornadas", "bruto", "despesas",
            "liquido", "recarga", "combustivel",
            "outras_despesas"
        ):
            total = sum(
                item[campo]
                for item in financeiro[grupo].values()
            )

            if total != f[campo]:
                raise ValueError(
                    f"Total divergente: {grupo}/{campo}"
                )


def gerar_relatorios(banco, destino, dia):
    banco = Path(banco).expanduser().resolve()
    destino = Path(destino).expanduser().resolve()

    inicio, fim = limites_operacionais(dia)

    if fim > datetime.now(FUSO):
        raise ValueError("Periodo operacional ainda aberto.")

    if not banco.is_file():
        raise FileNotFoundError("Banco nao encontrado.")

    destino.mkdir(
        parents=True,
        exist_ok=True,
        mode=0o700
    )

    pasta_final = destino / dia

    if pasta_final.exists():
        raise FileExistsError(
            f"Relatorios ja existentes: {pasta_final}"
        )

    log.info("Referencia: %s", dia)
    log.info("Periodo: %s ate %s", inicio, fim)

    db = sqlite3.connect(
        banco.as_uri() + "?mode=ro",
        uri=True,
        timeout=10
    )

    db.row_factory = sqlite3.Row

    try:
        db.execute("PRAGMA query_only = ON")
        db.execute("BEGIN")

        if db.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0] != "ok":
            raise RuntimeError("Banco inconsistente.")

        for registro in db.execute("""
            SELECT id, data_fim
            FROM jornadas
            WHERE status = 'ENCERRADA'
        """):
            try:
                horario = datetime.fromisoformat(
                    registro["data_fim"]
                )

                if horario.utcoffset() is None:
                    raise ValueError("Horario sem fuso.")

            except (TypeError, ValueError):
                raise ValueError(
                    "Horario inconsistente na jornada "
                    f"{registro['id']}"
                )

        jornadas = consultar_jornadas(db, dia)

        financeiro = consolidar_financeiro(db, dia)
        produtividade = consolidar_produtividade(db, dia)

        validar(financeiro, produtividade, jornadas)

        log.info("Jornadas conferidas: %s", len(jornadas))

    finally:
        db.close()

    with tempfile.TemporaryDirectory(
        prefix=".geracao_",
        dir=destino
    ) as temporario:

        pasta = Path(temporario) / dia
        pasta.mkdir(mode=0o700)

        gerar_excel_financeiro(
            financeiro,
            pasta / "01_Relatorio_Financeiro.xlsx"
        )

        gerar_excel_produtividade(
            produtividade,
            pasta / "02_Relatorio_Produtividade.xlsx"
        )

        gerar_pdf_executivo(
            financeiro,
            produtividade,
            pasta / "04_Relatorio_Executivo.pdf"
        )

        arquivos = list(pasta.iterdir())

        if len(arquivos) != 3:
            raise RuntimeError("Geracao incompleta.")

        for arquivo in arquivos:
            if arquivo.stat().st_size == 0:
                raise RuntimeError(
                    f"Arquivo vazio: {arquivo.name}"
                )

            arquivo.chmod(0o600)

        if pasta_final.exists():
            raise FileExistsError(
                "Destino ja existente."
            )

        pasta.rename(pasta_final)

    log.info("Relatorios publicados: %s", pasta_final)

    return pasta_final


def main():
    os.umask(0o077)

    parser = argparse.ArgumentParser(
        description="Relatorios diarios ER Transporte"
    )

    parser.add_argument("--banco", required=True)
    parser.add_argument("--destino", required=True)
    parser.add_argument("--data", default=None)

    args = parser.parse_args()

    try:
        gerar_relatorios(
            args.banco,
            args.destino,
            args.data or data_referencia()
        )

    except Exception:
        log.exception("Falha na geracao dos relatorios.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
