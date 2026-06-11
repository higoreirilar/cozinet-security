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
# ROOT
# =========================
@app.route("/")
def root():
    return redirect("/dashboard")

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
        SELECT COUNT(*)
        FROM pedidos
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
        SELECT id, order_id, cliente, cpf, email,
               ip, valor, score_risco, status
        FROM pedidos
        ORDER BY id DESC
        LIMIT 50
    """)

    pedidos = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("dashboard.html",
        usuario=session.get("nome"),
        total=total,
        aprovados=aprovados,
        analise=analise,
        bloqueados=bloqueados,
        protegido=protegido,
        score=score,
        pedidos=pedidos
    )

# =========================
# BLOQUEIO
# =========================
@app.route("/bloquear-ip", methods=["POST"])
def bloquear():
    ip = request.json.get("ip")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO ips_bloqueados(ip, motivo)
        VALUES(%s,'manual')
        ON CONFLICT(ip) DO NOTHING
    """, (ip,))

    cur.execute("""
        UPDATE pedidos SET status='bloqueado' WHERE ip=%s
    """, (ip,))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"ok": True})

# =========================
# DESBLOQUEIO
# =========================
@app.route("/desbloquear-ip", methods=["POST"])
def desbloquear():
    ip = request.json.get("ip")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM ips_bloqueados WHERE ip=%s", (ip,))
    cur.execute("UPDATE pedidos SET status='analise' WHERE ip=%s", (ip,))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"ok": True})

# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
