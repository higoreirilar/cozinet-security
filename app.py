from flask import Flask, request, jsonify, render_template, session, redirect
import os
import psycopg2
import time

app = Flask(__name__)
app.secret_key = "cozinet_saas_2026"

START_TIME = time.time()

# =========================
# DB CONNECTION
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
# ROOT ROUTE (FIX 404)
# =========================
@app.route("/")
def home():
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
# DASHBOARD SAFE
# =========================
@app.route("/dashboard")
def dashboard():

    if not login_required():
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor()

    # TOTAL
    cur.execute("SELECT COUNT(*) FROM pedidos")
    total_pedidos = cur.fetchone()[0]

    # APROVADOS
    cur.execute("SELECT COUNT(*) FROM pedidos WHERE status='aprovado'")
    aprovados = cur.fetchone()[0]

    # ANALISE
    cur.execute("SELECT COUNT(*) FROM pedidos WHERE status='analise'")
    analise = cur.fetchone()[0]

    # BLOQUEADOS (SAFE)
    cur.execute("""
        SELECT COUNT(*)
        FROM pedidos
        WHERE ip IN (SELECT ip FROM ips_bloqueados)
    """)
    bloqueados = cur.fetchone()[0]

    # VALOR PROTEGIDO
    cur.execute("""
        SELECT COALESCE(SUM(valor),0)
        FROM pedidos
        WHERE ip IN (SELECT ip FROM ips_bloqueados)
    """)
    valor_protegido = float(cur.fetchone()[0] or 0)

    # SCORE MÉDIO
    cur.execute("""
        SELECT COALESCE(ROUND(AVG(score_risco),2),0)
        FROM pedidos
    """)
    score_medio = cur.fetchone()[0]

    # LISTA PEDIDOS
    cur.execute("""
        SELECT id, order_id, cliente, cpf, email,
               ip, valor, score_risco, status,
               motivo, created_at
        FROM pedidos
        ORDER BY id DESC
        LIMIT 100
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    pedidos = []
    for r in rows:
        pedidos.append({
            "id": r[0],
            "order_id": r[1],
            "cliente": r[2],
            "cpf": r[3],
            "email": r[4],
            "ip": r[5],
            "valor": float(r[6]) if r[6] else 0,
            "score_risco": r[7],
            "status": r[8],
            "motivo": r[9],
            "created_at": str(r[10])
        })

    return render_template(
        "dashboard.html",
        usuario=session.get("nome"),
        total_pedidos=total_pedidos,
        aprovados=aprovados,
        analise=analise,
        bloqueados=bloqueados,
        valor_protegido=valor_protegido,
        score_medio=score_medio,
        pedidos=pedidos
    )

# =========================
# BLOQUEAR IP
# =========================
@app.route("/bloquear-ip", methods=["POST"])
def bloquear_ip():

    if not login_required():
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json() or {}
    ip = data.get("ip")

    if not ip:
        return jsonify({"error": "ip missing"}), 400

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO ips_bloqueados(ip, motivo)
        VALUES(%s,%s)
        ON CONFLICT(ip) DO NOTHING
    """, (ip, "manual"))

    cur.execute("""
        UPDATE pedidos
        SET status='bloqueado'
        WHERE ip=%s
    """, (ip,))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"ok": True})

# =========================
# DESBLOQUEAR IP
# =========================
@app.route("/desbloquear-ip", methods=["POST"])
def desbloquear_ip():

    if not login_required():
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json() or {}
    ip = data.get("ip")

    if not ip:
        return jsonify({"error": "ip missing"}), 400

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM ips_bloqueados WHERE ip=%s", (ip,))

    cur.execute("""
        UPDATE pedidos
        SET status='analise'
        WHERE ip=%s
    """, (ip,))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"ok": True})

# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
