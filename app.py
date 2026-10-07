from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login_motorista", methods=["GET", "POST"])
def login_motorista():

    mensagem = ""

    if request.method == "POST":
        usuario = request.form.get("usuario")
        senha = request.form.get("senha")

        if usuario == "motorista" and senha == "1234":
            return redirect(url_for("area_motorista"))

        mensagem = "Usuário ou senha inválidos."

    return render_template("login_motorista.html", mensagem=mensagem)


@app.route("/motorista")
def area_motorista():
    return render_template("motorista.html")


if __name__ == "__main__":
    app.run(debug=True)

