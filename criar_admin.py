from getpass import getpass
from werkzeug.security import generate_password_hash
from database import conectar

usuario = input("Usuário do administrador: ").strip().lower()
senha = getpass("Senha: ")
confirmacao = getpass("Confirme a senha: ")

if len(usuario) < 3:
    print("O usuário deve ter pelo menos 3 caracteres.")
elif len(senha) < 8:
    print("A senha deve ter pelo menos 8 caracteres.")
elif senha != confirmacao:
    print("As senhas não conferem.")
else:
    db = conectar()
    try:
        db.execute(
            """
            INSERT INTO administradores (usuario, senha_hash, ativo)
            VALUES (?, ?, 1)
            """,
            (usuario, generate_password_hash(senha))
        )
        db.commit()
        print("Administrador cadastrado com sucesso!")
    except Exception as erro:
        db.rollback()
        print("Não foi possível cadastrar:", erro)
    finally:
        db.close()
