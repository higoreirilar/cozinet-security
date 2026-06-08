from flask import Flask, request, jsonify, render_template, session, redirect
import os
import psycopg2
from psycopg2 import OperationalError
from antifraude import calcular_score

app = Flask(__name__)
app.secret_key = "cozinet_secret_key_2026"

# ---------------- CONEXÃO SEGURA ----------------
def get_conn():
    try:
        return psycopg2.connect(
            dbname=os.getenv("PGDATABASE"),
            user=os.getenv("PGUSER"),
            password=os.getenv("PGPASSWORD"),
            host=os.getenv("PGHOST"),
            port=os.getenv("PGPORT")
        )
    except Exception as e:
        print("❌ ERRO CONEXÃO BANCO:", e)
        return None

# ---------------- AUTH ----------------
def login_required():
    return session.get("user_id") is not None


# ---------------- CADASTRO ----------------
@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        nome = request.form["nome"]
        email = request.form["email"]
        senha = request.form["senha"]

        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO usuarios (nome, email, senha)
            VALUES (%s, %s, %s)
        """, (nome, email, senha))

        conn.commit()
        cur.close()
        conn.close()

        return redirect("/login")

    return render_template("cadastro.html")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        senha = request.form["senha"]

        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, nome, role FROM usuarios
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

        return "Login inválido"

    return render_template("login.html")


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ---------------- STATUS ----------------
def definir_status(score):
    if score >= 60:
        return "bloqueado"
    elif score >= 30:
        return "analise"
    return "aprovado"


# ---------------- SALVAR PEDIDO ----------------
def salvar(order_id, ip, valor, status, motivos):
    conn = get_conn()
    if not conn:
        print("❌ banco indisponível")
        return

    cur = conn.cursor()

    cur.execute("""
        INSERT INTO pedidos (order_id, ip, valor, status, motivo, created_at)
        VALUES (%s, %s, %s, %s, %s, NOW())
    """, (order_id, ip, valor, status, ",".join(motivos)))

    conn.commit()
    cur.close()
    conn.close()


# ---------------- WEBHOOK ----------------
@app.route("/webhook/tray", methods=["POST"])
def webhook():
    data = request.json or {}

    order_id = data.get("order_id", "unknown")
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    valor = float(data.get("total", 0))

    score, motivos = calcular_score(ip, valor)
    status = definir_status(score)

    salvar(order_id, ip, valor, status, motivos)

    return jsonify({
        "order_id": order_id,
        "score": score,
        "status": status,
        "motivos": motivos
    })


# ---------------- PAINEL ----------------
@app.route("/painel")
def painel():
    if not login_required():
        return redirect("/login")

    return render_template("painel.html", usuario=session.get("nome"))


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if not login_required():
        return jsonify({"error": "unauthorized"}), 401

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, order_id, ip, valor, status, motivo, created_at
        FROM pedidos
        ORDER BY id DESC
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify([
        {
            "id": r[0],
            "order_id": r[1],
            "ip": r[2],
            "valor": float(r[3]),
            "status": r[4],
            "motivos": r[5],
            "created_at": str(r[6])
        }
        for r in rows
    ])


# ---------------- FRAUDES ----------------
@app.route("/fraudes")
def fraudes():
    if not login_required():
        return jsonify({"error": "unauthorized"}), 401

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, order_id, ip, valor, status, motivo, created_at
        FROM pedidos
        WHERE status = 'bloqueado'
        ORDER BY id DESC
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify([
        {
            "id": r[0],
            "order_id": r[1],
            "ip": r[2],
            "valor": float(r[3]),
            "status": r[4],
            "motivos": r[5],
            "created_at": str(r[6])
        }
        for r in rows
    ])


# ---------------- CONFIG ----------------
@app.route("/config")
def config():
    return jsonify({
        "sistema": "Cozinet Antifraude SaaS",
        "status": "online",
        "modo": "produção"
    })


# ---------------- STATUS ----------------
@app.route("/status")
def status():
    return "OK - Cozinet rodando"


# ---------------- HOME ----------------
@app.route("/")
def home():
    return "Cozinet SaaS Antifraude Online 🚀"


# ---------------- START ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
