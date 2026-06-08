from flask import Flask, request, jsonify, render_template
import os
import psycopg2
from psycopg2 import OperationalError
from antifraude import calcular_score

app = Flask(__name__)

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
def salvar(order_id, ip, valor, status, motivos):
    conn = get_conn()
    if not conn:
        print("❌ banco indisponível, não salvou pedido")
        return

    try:
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

    except Exception as e:
        print("❌ erro ao salvar:", e)

# ---------------- WEBHOOK ----------------
@app.route("/webhook/tray", methods=["POST"])
def webhook():
    try:
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

    except Exception as e:
        print("❌ erro webhook:", e)
        return jsonify({"error": "webhook failure"}), 500

# ---------------- PAINEL SPA ----------------
@app.route("/painel")
def painel():
    return render_template("painel.html")

# ---------------- DASHBOARD API ----------------
@app.route("/dashboard")
def dashboard():
    conn = get_conn()
    if not conn:
        return jsonify([])

    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id, order_id, ip, valor, status, motivo, created_at
            FROM pedidos
            ORDER BY id DESC
        """)
        rows = cur.fetchall()

    except Exception as e:
        print("❌ erro SELECT:", e)
        rows = []

    finally:
        cur.close()
        conn.close()

    resultado = []
    for r in rows:
        resultado.append({
            "id": r[0],
            "order_id": r[1],
            "ip": r[2],
            "valor": float(r[3]) if r[3] else 0,
            "status": r[4],
            "motivos": r[5],
            "created_at": str(r[6]) if len(r) > 6 and r[6] else ""
        })

    return jsonify(resultado)

# ---------------- PEDIDOS ----------------
@app.route("/pedidos")
def pedidos():
    return dashboard()

# ---------------- FRAUDES ----------------
@app.route("/fraudes")
def fraudes():
    conn = get_conn()
    if not conn:
        return jsonify([])

    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id, order_id, ip, valor, status, motivo, created_at
            FROM pedidos
            WHERE status = 'bloqueado'
            ORDER BY id DESC
        """)
        rows = cur.fetchall()

    except Exception as e:
        print("❌ erro fraudes:", e)
        rows = []

    finally:
        cur.close()
        conn.close()

    return jsonify([
        {
            "id": r[0],
            "order_id": r[1],
            "ip": r[2],
            "valor": float(r[3]) if r[3] else 0,
            "status": r[4],
            "motivos": r[5],
            "created_at": str(r[6]) if len(r) > 6 and r[6] else ""
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

# ---------------- HEALTHCHECK ----------------
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
