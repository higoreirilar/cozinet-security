from flask import Flask, request, jsonify, render_template, session, redirect
import os
import psycopg2

app = Flask(__name__)
app.secret_key = "cozinet_saas_2026"

# ---------------- BANCO ----------------
def get_conn():
    return psycopg2.connect(
        dbname=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        host=os.getenv("PGHOST"),
        port=os.getenv("PGPORT")
    )

# ---------------- LOGIN ----------------
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
            return redirect("/painel")

        return render_template("login.html", erro="Login inválido")

    return render_template("login.html")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- PROTEÇÃO ----------------
def login_required():
    return session.get("user_id") is not None

# ---------------- PAINEL ----------------
@app.route("/painel")
def painel():
    if not login_required():
        return redirect("/login")

    return render_template(
        "painel.html",
        usuario=session.get("nome")
    )

# ---------------- DASHBOARD API ----------------
@app.route("/dashboard")
def dashboard():

    if not login_required():
        return jsonify({"error": "unauthorized"}), 401

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            order_id,
            ip,
            valor,
            status,
            motivo,
            created_at
        FROM pedidos
        ORDER BY id DESC
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    data = []

    for r in rows:
        data.append({
            "id": r[0],
            "order_id": r[1],
            "ip": r[2],
            "valor": float(r[3]) if r[3] else 0,
            "status": r[4],
            "motivo": r[5],
            "created_at": str(r[6])
        })

    return jsonify(data)

# ---------------- API RESUMO ----------------
@app.route("/stats")
def stats():

    if not login_required():
        return jsonify({"error": "unauthorized"}), 401

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT status FROM pedidos")

    rows = cur.fetchall()

    cur.close()
    conn.close()

    aprovados = sum(1 for r in rows if r[0] == "aprovado")
    analise = sum(1 for r in rows if r[0] == "analise")
    bloqueados = sum(1 for r in rows if r[0] == "bloqueado")

    return jsonify({
        "aprovados": aprovados,
        "analise": analise,
        "bloqueados": bloqueados
    })

# ---------------- BLOQUEAR IP ----------------
@app.route("/bloquear-ip", methods=["POST"])
def bloquear_ip():

    if not login_required():
        return jsonify({"error": "unauthorized"}), 401

    dados = request.get_json()
    ip = dados.get("ip")

    if not ip:
        return jsonify({"error": "ip obrigatório"}), 400

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ips_bloqueados (
            id SERIAL PRIMARY KEY,
            ip VARCHAR(100) UNIQUE,
            motivo TEXT,
            data_bloqueio TIMESTAMP DEFAULT NOW()
        )
    """)

    cur.execute("""
        INSERT INTO ips_bloqueados (
            ip,
            motivo
        )
        VALUES (%s,%s)
        ON CONFLICT (ip) DO NOTHING
    """, (
        ip,
        "Bloqueio manual pelo administrador"
    ))

    conn.commit()

    cur.close()
    conn.close()

    return jsonify({
        "success": True,
        "message": f"IP {ip} bloqueado com sucesso"
    })

# ---------------- LISTAR IPS BLOQUEADOS ----------------
@app.route("/ips-bloqueados")
def listar_ips_bloqueados():

    if not login_required():
        return jsonify({"error": "unauthorized"}), 401

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            ip,
            motivo,
            data_bloqueio
        FROM ips_bloqueados
        ORDER BY data_bloqueio DESC
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify([
        {
            "id": r[0],
            "ip": r[1],
            "motivo": r[2],
            "data": str(r[3])
        }
        for r in rows
    ])

# ---------------- DESBLOQUEAR IP ----------------
@app.route("/desbloquear-ip", methods=["POST"])
def desbloquear_ip():

    if not login_required():
        return jsonify({"error": "unauthorized"}), 401

    dados = request.get_json()
    ip = dados.get("ip")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM ips_bloqueados
        WHERE ip=%s
    """, (ip,))

    conn.commit()

    cur.close()
    conn.close()

    return jsonify({
        "success": True,
        "message": f"IP {ip} removido da lista de bloqueio"
    })

# ---------------- HOME ----------------
@app.route("/")
def home():
    return redirect("/login")

# ---------------- START ----------------
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8000
    )
