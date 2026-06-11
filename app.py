from flask import Flask, request, jsonify, render_template, session, redirect
import os
import psycopg2
import time

app = Flask(__name__)
app.secret_key = "cozinet_saas_2026"

START_TIME = time.time()

# =========================
# DB
# =========================
def get_conn():
    return psycopg2.connect(
        dbname=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        host=os.getenv("PGHOST"),
        port=os.getenv("PGPORT")
    )

def login_required():
    return "user_id" in session

# =========================
# LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        senha = request.form.get("senha")

        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, nome, role
            FROM usuarios
            WHERE email=%s AND senha=%s
        """, (email, senha))

        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["nome"] = user[1]
            session["role"] = user[2]
            return redirect("/dashboard")

        return render_template("login.html", erro="Login inválido")

    return render_template("login.html")

# =========================
# DASHBOARD
# =========================
@app.route("/dashboard")
def dashboard():
    if not login_required():
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM pedidos")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM pedidos WHERE status='aprovado'")
    aprovados = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM pedidos WHERE status='analise'")
    analise = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM pedidos
        WHERE ip IN (SELECT ip FROM ips_bloqueados)
    """)
    bloqueados = cur.fetchone()[0]

    cur.execute("""
        SELECT COALESCE(SUM(valor),0)
        FROM pedidos
        WHERE ip IN (SELECT ip FROM ips_bloqueados)
    """)
    protegido = float(cur.fetchone()[0] or 0)

    cur.execute("""
        SELECT COALESCE(ROUND(AVG(score_risco),2),0)
        FROM pedidos
    """)
    score = cur.fetchone()[0]

    cur.execute("""
        SELECT id, order_id, cliente, cpf, email, ip, valor, score_risco, status
        FROM pedidos
        ORDER BY id DESC
        LIMIT 50
    """)

    pedidos = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "dashboard.html",
        usuario=session["nome"],
        total=total,
        aprovados=aprovados,
        analise=analise,
        bloqueados=bloqueados,
        protegido=protegido,
        score=score,
        pedidos=pedidos
    )

# =========================
# BLOQUEADOS
# =========================
@app.route("/bloqueados")
def bloqueados():
    if not login_required():
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, ip, motivo, data_bloqueio
        FROM ips_bloqueados
        ORDER BY id DESC
    """)

    dados = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "bloqueados.html",
        usuario=session["nome"],
        bloqueados=dados
    )

# =========================
# DESBLOQUEAR
# =========================
@app.route("/desbloquear-ip", methods=["POST"])
def desbloquear():
    ip = request.get_json().get("ip")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM ips_bloqueados WHERE ip=%s", (ip,))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"ok": True})

# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
