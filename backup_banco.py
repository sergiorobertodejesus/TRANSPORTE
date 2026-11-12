#!/usr/bin/env python3
"""Backup consistente do SQLite da ER Transporte.

Uso:
  ER_AMBIENTE=teste python backup_banco.py
  ER_AMBIENTE=producao python backup_banco.py --destino /home/ubuntu/backups/er-transporte

A retenção remove apenas arquivos com prefixo er_auto_ criados por esta rotina.
"""
import argparse
import fcntl
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PREFIXO = 'er_auto_'


def executar():
    parser = argparse.ArgumentParser(description='Backup verificado do banco SQLite ER Transporte')
    parser.add_argument('--destino', type=Path, help='Pasta de backups; padrão: backups/ no projeto')
    parser.add_argument('--retencao-dias', type=int, default=14)
    args = parser.parse_args()
    if args.retencao_dias < 1:
        parser.error('--retencao-dias deve ser pelo menos 1')

    ambiente = os.environ.get('ER_AMBIENTE', '').strip().lower()
    if ambiente not in ('teste', 'producao'):
        parser.error('Defina explicitamente ER_AMBIENTE=teste ou ER_AMBIENTE=producao')

    raiz = Path(__file__).resolve().parent
    origem = raiz / ('transporte_teste.db' if ambiente == 'teste' else 'transporte.db')
    if not origem.is_file():
        raise FileNotFoundError(f'Banco não encontrado: {origem}')

    destino_dir = (args.destino or (raiz / 'backups')).expanduser().resolve()
    destino_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(destino_dir, 0o700)
    trava = destino_dir / '.er_backup.lock'

    with trava.open('a+') as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('Outro backup está em andamento; encerrando sem executar.', file=sys.stderr)
            return 2

        agora = datetime.now(timezone.utc)
        nome = f'{PREFIXO}{ambiente}_{agora:%Y%m%dT%H%M%S_%fZ}.db'
        final = destino_dir / nome
        parcial = destino_dir / (nome + '.partial')
        try:
            with sqlite3.connect(origem.resolve().as_uri() + '?mode=ro', uri=True, timeout=30) as fonte:
                with sqlite3.connect(parcial, timeout=30) as copia:
                    fonte.backup(copia, pages=100, sleep=0.1)
                    resultado = copia.execute('PRAGMA integrity_check').fetchone()[0]
                    if resultado != 'ok':
                        raise RuntimeError(f'Integridade inválida: {resultado}')
            os.chmod(parcial, 0o600)
            parcial.replace(final)
            print(f'BACKUP OK: {final} ({final.stat().st_size} bytes); integridade: ok')
        except Exception:
            parcial.unlink(missing_ok=True)
            raise

        limite = agora - timedelta(days=args.retencao_dias)
        removidos = 0
        # Apenas backups automáticos deste mesmo ambiente; arquivos manuais preservados.
        for arquivo in destino_dir.glob(f'{PREFIXO}{ambiente}_*.db'):
            if arquivo == final or not arquivo.is_file() or arquivo.is_symlink():
                continue
            try:
                if datetime.fromtimestamp(arquivo.stat().st_mtime, timezone.utc) < limite:
                    arquivo.unlink()
                    removidos += 1
            except OSError as erro:
                print(f'AVISO: não foi possível remover {arquivo.name}: {erro}', file=sys.stderr)
        print(f'Retenção: {args.retencao_dias} dias; backups antigos removidos: {removidos}')
        return 0


if __name__ == '__main__':
    try:
        sys.exit(executar())
    except Exception as erro:
        print(f'ERRO NO BACKUP: {erro}', file=sys.stderr)
        sys.exit(1)
