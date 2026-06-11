import os
import time
import psycopg2
from flask import Flask, render_template, request, redirect, session, url_for, jsonify

app = Flask(__name__)
app.secret_key = "secret-key-change"

DATABASE_URL = os.getenv("DATABASE_URL")

def db():
    return psycopg2.connect(DATABASE_URL)

# ---------------------------
# HOME -> vai pro login
# ---------------------------
@app.route("/")
def home():
    return redirect("/login")


# ---------------------------
# LOGIN
# ---------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        email = request.form["email"]
        senha = request.form["senha"]

        conn = db()
        cur = conn.cursor()
        cur.execute("SELECT id FROM usuarios WHERE email=%s AND senha=%s", (email, senha))
        user = cur.fetchone()
        conn.close()

        if user:
            session["user"] = email
            return redirect("/dashboard")
        else:
            error = "Credenciais inválidas"

    return render_template("login.html", error=error)


# ---------------------------
# DASHBOARD
# ---------------------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM pedidos ORDER BY id DESC LIMIT 50")
    rows = cur.fetchall()

    cols = [desc[0] for desc in cur.description]
    pedidos = [dict(zip(cols, r)) for r in rows]

    # stats seguras (sem quebrar)
    cur.execute("SELECT COUNT(*) FROM pedidos")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM pedidos WHERE status='APROVADO'")
    aprovados = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM pedidos WHERE status='ANÁLISE'")
    analise = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM pedidos WHERE status='RECUSADO'")
    recusados = cur.fetchone()[0]

    conn.close()

    system = {
        "status": "online",
        "host": request.host,
        "uptime": int(time.time()),
        "hostname": os.uname().nodename,
        "port": 8080,
        "env": "production"
    }

    return render_template(
        "dashboard.html",
        pedidos=pedidos,
        total=total,
        aprovados=aprovados,
        analise=analise,
        recusados=recusados,
        system=system
    )


# ---------------------------
# LOGOUT
# ---------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ---------------------------
# BLOQUEAR IP
# ---------------------------
@app.route("/bloquear_ip", methods=["POST"])
def bloquear_ip():
    ip = request.json["ip"]

    conn = db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO ips_bloqueados (ip, motivo, data_bloqueio) VALUES (%s,%s, NOW())",
        (ip, "bloqueio manual")
    )
    conn.commit()
    conn.close()

    return jsonify({"ok": True})


# ---------------------------
# DESBLOQUEAR IP
# ---------------------------
@app.route("/desbloquear_ip", methods=["POST"])
def desbloquear_ip():
    ip = request.json["ip"]

    conn = db()
    cur = conn.cursor()
    cur.execute("DELETE FROM ips_bloqueados WHERE ip=%s", (ip,))
    conn.commit()
    conn.close()

    return jsonify({"ok": True})


# ---------------------------
# LOGS
# ---------------------------
@app.route("/logs")
def logs():
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 100")
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    logs = [dict(zip(cols, r)) for r in rows]
    conn.close()

    return render_template("logs.html", logs=logs)


# ---------------------------
# BLOCKED / TRUSTED
# ---------------------------
@app.route("/bloqueados")
def bloqueados():
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ips_bloqueados ORDER BY id DESC")
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    data = [dict(zip(cols, r)) for r in rows]
    conn.close()

    return render_template("bloqueados.html", data=data)


@app.route("/ips_confiaveis")
def confiaveis():
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ips_confiaveis ORDER BY id DESC")
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    data = [dict(zip(cols, r)) for r in rows]
    conn.close()

    return render_template("ips_confiaveis.html", data=data)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
