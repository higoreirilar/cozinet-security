from flask import Flask, request, jsonify, render_template
import os
import psycopg2
from antifraude import calcular_score

app = Flask(__name__)

# ---------------- BANCO ----------------
def get_conn():
    return psycopg2.connect(
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        host=os.environ["PGHOST"],
        port=os.environ["PGPORT"]
    )

# ---------------- STATUS ----------------
def definir_status(score):
    if score >= 60:
        return "bloqueado"
    elif score >= 30:
        return "analise"
    return "aprovado"

# ---------------- DEVICE ----------------
def detectar_device(user_agent):
    ua = (user_agent or "").lower()
    if "mobile" in ua or "android" in ua or "iphone" in ua:
        return "mobile"
    return "desktop"

# ---------------- SALVAR PEDIDO ----------------
def salvar(order_id, ip, valor, status, motivos, device):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO pedidos (order_id, ip, valor, status, motivo, created_at)
        VALUES (%s, %s, %s, %s, %s, NOW())
    """, (
        order_id,
        ip,
        valor,
        status,
        ",".join(motivos)
    ))

    conn.commit()
    cur.close()
    conn.close()

# ---------------- WEBHOOK ----------------
@app.route("/webhook/tray", methods=["POST"])
def webhook():
    data = request.json

    order_id = data.get("order_id")
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    valor = float(data.get("total", 0))

    score, motivos = calcular_score(ip, valor)
    status = definir_status(score)

    device = detectar_device(request.headers.get("User-Agent"))

    salvar(order_id, ip, valor, status, motivos, device)

    return jsonify({
        "order_id": order_id,
        "score": score,
        "status": status,
        "motivos": motivos,
        "device": device
    })

# ---------------- DASHBOARD (SPA FRONTEND DATA) ----------------
@app.route("/dashboard")
def dashboard():
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

# ---------------- SPA PAINEL ----------------
@app.route("/painel")
def painel():
    return render_template("painel.html")

# ---------------- PEDIDOS (ABA SPA) ----------------
@app.route("/pedidos")
def pedidos():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM pedidos ORDER BY id DESC")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify(rows)

# ---------------- FRAUDES (ABA SPA) ----------------
@app.route("/fraudes")
def fraudes():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM pedidos
        WHERE status = 'bloqueado'
        ORDER BY id DESC
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify(rows)

# ---------------- CONFIG ----------------
@app.route("/config")
def config():
    return jsonify({
        "sistema": "Cozinet Antifraude SaaS",
        "status": "ativo",
        "modo": "produção"
    })

# ---------------- HOME ----------------
@app.route("/")
def home():
    return "Cozinet SaaS Antifraude Online 🚀"

# ---------------- START ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
