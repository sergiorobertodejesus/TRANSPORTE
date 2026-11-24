import os
import sys
import time
import shutil
import sqlite3
import tempfile
import unittest
import subprocess
from pathlib import Path
from contextlib import closing


class TestBackup(unittest.TestCase):

    def test_backup_recuperacao_retencao(self):
        self.assertEqual(os.environ.get("ER_AMBIENTE"), "teste")

        with tempfile.TemporaryDirectory() as pasta:
            raiz = Path(pasta)
            script = raiz / "backup_banco.py"
            origem = raiz / "transporte_teste.db"
            destino = raiz / "backups"

            shutil.copy2(
                Path(__file__).resolve().parents[1] / "backup_banco.py",
                script
            )

            with closing(sqlite3.connect(origem)) as banco:
                banco.execute("""
                    CREATE TABLE jornadas (
                        id INTEGER PRIMARY KEY,
                        motorista TEXT,
                        faturamento REAL
                    )
                """)
                banco.execute(
                    "INSERT INTO jornadas VALUES (?, ?, ?)",
                    (1, "Motorista Teste", 500.0)
                )
                banco.commit()

            destino.mkdir()

            antigo = destino / "er_auto_teste_antigo.db"
            manual = destino / "backup_manual.db"
            outro = destino / "er_auto_producao_antigo.db"

            for item in (antigo, manual, outro):
                item.write_bytes(b"arquivo ficticio")
                data = time.time() - 20 * 86400
                os.utime(item, (data, data))

            comando = [
                sys.executable, str(script),
                "--destino", str(destino),
                "--retencao-dias", "14"
            ]

            ambiente = dict(os.environ)
            ambiente.pop("ER_AMBIENTE", None)

            recusado = subprocess.run(
                comando, env=ambiente,
                capture_output=True, text=True
            )
            self.assertNotEqual(recusado.returncode, 0)
            self.assertTrue(antigo.exists())

            ambiente["ER_AMBIENTE"] = "teste"

            resultado = subprocess.run(
                comando, env=ambiente,
                capture_output=True, text=True
            )

            self.assertEqual(
                resultado.returncode, 0,
                resultado.stderr
            )
            self.assertIn("BACKUP OK", resultado.stdout)

            backups = list(destino.glob("er_auto_teste_*.db"))
            self.assertEqual(len(backups), 1)

            backup = backups[0]

            self.assertFalse(antigo.exists())
            self.assertTrue(manual.exists())
            self.assertTrue(outro.exists())

            self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
            self.assertEqual(destino.stat().st_mode & 0o777, 0o700)
            self.assertEqual(list(destino.glob("*.partial")), [])

            restaurado = raiz / "restaurado.db"

            with closing(sqlite3.connect(
                backup.as_uri() + "?mode=ro", uri=True
            )) as fonte:
                with closing(sqlite3.connect(restaurado)) as copia:
                    fonte.backup(copia)

            for caminho in (origem, restaurado):
                with closing(sqlite3.connect(caminho)) as banco:
                    integridade = banco.execute(
                        "PRAGMA integrity_check"
                    ).fetchone()[0]

                    registros = banco.execute(
                        "SELECT * FROM jornadas"
                    ).fetchall()

                    self.assertEqual(integridade, "ok")
                    self.assertEqual(
                        registros,
                        [(1, "Motorista Teste", 500.0)]
                    )


if __name__ == "__main__":
    unittest.main()
