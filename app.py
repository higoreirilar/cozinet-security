from flask import Flask, request, jsonify
import os
import psycopg2
from antifraude import check_fraude

app = Flask(__name__)

# -------- BANCO --------
def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])

def salvar_pedido(ip, valor, status):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO pedidos (cliente_id, ip, valor, status)
        VALUES (1, %s, %s, %s)
    """, (ip, valor, status))

    conn.commit()
    cur.close()
    conn.close()

# -------- ROTAS --------

@app.route("/")
def home():
    return "Cozinet API rodando"

@app.route("/compra", methods=["POST"])
def compra():
    data = request.json

    ip = data.get("ip")
    valor = data.get("valor")

    # antifraude
    resultado = check_fraude(ip, valor)

    status = "bloqueado" if resultado["fraude"] else "aprovado"

    salvar_pedido(ip, valor, status)

    return jsonify(resultado)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
