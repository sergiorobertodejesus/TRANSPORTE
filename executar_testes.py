import os
import sys
import unittest

if os.environ.get("ER_AMBIENTE") != "teste":
    print(
        "BLOQUEADO: execute com ER_AMBIENTE=teste.",
        file=sys.stderr
    )
    sys.exit(1)

suite = unittest.defaultTestLoader.discover(
    start_dir="tests",
    pattern="test_*.py"
)

resultado = unittest.TextTestRunner(
    verbosity=2
).run(suite)

sys.exit(0 if resultado.wasSuccessful() else 1)
