from flask import Flask, request, jsonify, render_template 
import os
import psycopg2
from antifraude import calcular_score

app = Flask(__name__)

def get_conn():
    return psycopg2.connect(
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        host=os.environ["PGHOST"],
        port=os.environ["PGPORT"]
    )

def salvar(order_id, ip, valor, score, status, motivos):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO pedidos (order_id, ip, valor, status, motivo)
        VALUES (%s, %s, %s, %s, %s)
    """, (order_id, ip, valor, status, ",".join(motivos)))

    conn.commit()
    cur.close()
    conn.close()

def definir_status(score):
    if score >= 60:
        return "bloqueado"
    elif score >= 30:
        return "analise"
    return "aprovado"

@app.route("/webhook/tray", methods=["POST"])
def webhook():
    data = request.json

    order_id = data.get("order_id")
    ip = data.get("ip", "0.0.0.0")
    valor = data.get("total", 0)

    score, motivos = calcular_score(ip, valor)
    status = definir_status(score)

    salvar(order_id, ip, valor, score, status, motivos)

    # ALERTA ADMIN
    if status == "bloqueado":
        print(f"🚨 ALERTA FRAUDE: {order_id} SCORE {score}")

    return jsonify({
        "order_id": order_id,
        "score": score,
        "status": status,
        "motivos": motivos
    })

@app.route("/dashboard")
def dashboard():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM pedidos ORDER BY id DESC")
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
            "motivos": r[5]
        })

    return jsonify(resultado)


@app.route("/painel")
def painel():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM pedidos ORDER BY id DESC")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("painel.html", dados=rows)
def painel():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM pedidos ORDER BY id DESC")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("painel.html", dados=rows)
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM pedidos ORDER BY id DESC")
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
            "motivos": r[5]
        })

    return jsonify(resultado)

@app.route("/")
def home():
    return "Cozinet Antifraude v2 Online"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
