#!/usr/bin/env python3
"""Envia o backup SQLite mais recente ao Amazon S3."""

import os
import sqlite3
import subprocess
from pathlib import Path

if os.environ.get("ER_AMBIENTE") != "producao":
    raise SystemExit("Envio permitido somente em producao.")

pasta = Path("/home/ubuntu/backups/er-transporte")
bucket = "s3://er-transporte-backups-077712529519-us-east-2-an/banco/"

arquivos = sorted(
    arquivo for arquivo in pasta.glob("er_auto_producao_*.db")
    if arquivo.is_file() and not arquivo.is_symlink()
)

if not arquivos:
    raise SystemExit("Nenhum backup encontrado.")

backup = arquivos[-1]

db = sqlite3.connect(backup.as_uri() + "?mode=ro", uri=True)
try:
    integridade = db.execute("PRAGMA integrity_check").fetchone()[0]
finally:
    db.close()

if integridade != "ok":
    raise SystemExit("Backup com integridade invalida.")

print(f"Enviando backup: {backup.name}", flush=True)

subprocess.run([
    "/usr/local/bin/aws",
    "s3", "cp",
    str(backup),
    bucket + backup.name,
    "--region", "us-east-2",
    "--only-show-errors"
], check=True)

print(f"BACKUP S3 OK: {backup.name}", flush=True)
