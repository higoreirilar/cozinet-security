from flask import Flask, request, jsonify, render_template
import os
import psycopg2
from antifraude import calcular_score

app = Flask(__name__)

# ---------------- CONEXÃO BANCO ----------------
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

# ---------------- SALVAR PEDIDO ----------------
def salvar(order_id, ip, valor, status, motivos):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO pedidos (order_id, ip, valor, status, motivo)
        VALUES (%s, %s, %s, %s, %s)
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
    data = request.get_json(silent=True) or {}

    order_id = data.get("order_id")
    ip = data.get("ip", "0.0.0.0")
    valor = data.get("total", 0)

    score, motivos = calcular_score(ip, valor)
    status = definir_status(score)

    salvar(order_id, ip, valor, status, motivos)

    if status == "bloqueado":
        print(f"🚨 ALERTA FRAUDE: {order_id} SCORE {score}")

    return jsonify({
        "order_id": order_id,
        "ip": ip,
        "valor": valor,
        "score": score,
        "status": status,
        "motivos": motivos
    })

# ---------------- DASHBOARD JSON ----------------
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

    resultado = []
    for r in rows:
        resultado.append({
            "id": r[0],
            "order_id": r[1],
            "ip": r[2],
            "valor": r[3],
            "status": r[4],
            "motivos": r[5],
            "created_at": r[6]
        })

    return jsonify(resultado)

# ---------------- PAINEL HTML ----------------
@app.route("/painel")
def painel():
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

    return render_template("painel.html", dados=rows)

# ---------------- HOME ----------------
@app.route("/")
def home():
    return "🛡️ Cozinet Antifraude Online - Sistema Ativo"

# ---------------- START ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
