from flask import Flask, request, jsonify, render_template, session, redirect
import os
import psycopg2
import time
import socket

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
# AUTH
# =========================
def login_required():
    return "user_id" in session

# =========================
# SYSTEM INFO
# =========================
def system_info():
    return {
        "host": request.host,
        "uptime": round(time.time() - START_TIME, 2),
        "env": os.getenv("ENV", "production"),
        "port": request.environ.get("SERVER_PORT", "8000"),
        "hostname": socket.gethostname(),
        "status": "online"
    }

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
# DASHBOARD (COMPATÍVEL 100%)
# =========================
@app.route("/dashboard")
def dashboard():
    if not login_required():
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor()

    # COUNTS
    cur.execute("SELECT COUNT(*) FROM pedidos")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM pedidos WHERE status='aprovado'")
    aprovados = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM pedidos WHERE status='analise'")
    analise = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM pedidos WHERE status='bloqueado'")
    bloqueados = cur.fetchone()[0]

    # VALUE
    cur.execute("SELECT COALESCE(SUM(valor),0) FROM pedidos")
    valor_total = float(cur.fetchone()[0])

    # SCORE
    cur.execute("SELECT COALESCE(ROUND(AVG(score_risco),2),0) FROM pedidos")
    score_medio = cur.fetchone()[0]

    # PEDIDOS FULL (TODOS CAMPOS NOVOS)
    cur.execute("""
        SELECT
            id, order_id, cliente, cpf, email,
            telefone, cep, rua, bairro, cidade, estado,
            pais, dispositivo,
            ip, valor, score_risco, status,
            motivo, created_at, data_analise
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
            "telefone": r[5],
            "cep": r[6],
            "rua": r[7],
            "bairro": r[8],
            "cidade": r[9],
            "estado": r[10],
            "pais": r[11],
            "dispositivo": r[12],
            "ip": r[13],
            "valor": float(r[14]) if r[14] else 0,
            "score_risco": r[15],
            "status": r[16],
            "motivo": r[17],
            "created_at": str(r[18]),
            "data_analise": str(r[19]) if r[19] else None
        })

    return render_template(
        "dashboard.html",
        usuario=session.get("nome"),
        total_pedidos=total,
        aprovados=aprovados,
        analise=analise,
        bloqueados=bloqueados,
        valor_protegido=valor_total,
        score_medio=score_medio,
        pedidos=pedidos,
        system=system_info()
    )

# =========================
# BLOQUEIO IP
# =========================
@app.route("/bloquear-ip", methods=["POST"])
def bloquear_ip():
    if not login_required():
        return jsonify({"error": "unauthorized"}), 401

    ip = request.get_json().get("ip")

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
# DESBLOQUEIO
# =========================
@app.route("/desbloquear-ip", methods=["POST"])
def desbloquear_ip():
    if not login_required():
        return jsonify({"error": "unauthorized"}), 401

    ip = request.get_json().get("ip")

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
# RUN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
