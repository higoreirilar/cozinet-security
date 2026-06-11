from flask import Flask, request, jsonify, render_template, session, redirect
import os
import psycopg2
import time
import socket

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

# =========================
def login_required():
    return "user_id" in session

# =========================
def system_info():
    return {
        "status": "Online",
        "host": socket.gethostname(),
        "uptime": round(time.time() - START_TIME, 2),
        "env": os.getenv("ENV", "Production"),
        "port": "8080",
        "worker": "Gunicorn"
    }

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

    cur.execute("SELECT COUNT(*) FROM pedidos WHERE status='bloqueado'")
    bloqueados = cur.fetchone()[0]

    cur.execute("SELECT COALESCE(SUM(valor),0) FROM pedidos")
    valor = cur.fetchone()[0]

    cur.execute("SELECT COALESCE(ROUND(AVG(score_risco),2),0) FROM pedidos")
    score = cur.fetchone()[0]

    cur.execute("""
        SELECT id, order_id, cliente, cpf, email, ip, valor, score_risco, status
        FROM pedidos
        ORDER BY id DESC
        LIMIT 50
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    pedidos = [
        {
            "id": r[0],
            "order_id": r[1],
            "cliente": r[2],
            "cpf": r[3],
            "email": r[4],
            "ip": r[5],
            "valor": float(r[6]),
            "score_risco": r[7],
            "status": r[8],
        }
        for r in rows
    ]

    return render_template(
        "dashboard.html",
        usuario=session["nome"],
        total=total,
        aprovados=aprovados,
        analise=analise,
        bloqueados=bloqueados,
        valor=valor,
        score=score,
        pedidos=pedidos,
        system=system_info()
    )


# =========================
@app.route("/bloqueados")
def bloqueados():
    if not login_required():
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, ip, motivo, created_at
        FROM ips_bloqueados
        ORDER BY id DESC
    """)

    bloqueados = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "bloqueados.html",
        usuario=session["nome"],
        bloqueados=bloqueados
    )


# =========================
@app.route("/desbloquear-ip", methods=["POST"])
def desbloquear_ip():
    if not login_required():
        return jsonify({"error": "unauthorized"}), 401

    ip = request.get_json().get("ip")

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
    app.run(host="0.0.0.0", port=8000, debug=True)
