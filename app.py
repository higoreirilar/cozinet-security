from flask import Flask, request, jsonify
import psycopg2
import os

app = Flask(__name__)

def salvar_pedido(ip, valor):
    conn = psycopg2.connect(
        dbname="loja",
        user="postgres",
        password="@32426022",
        host="localhost",
        port="5432"
    )

    cur = conn.cursor()

    cur.execute("""
        INSERT INTO pedidos (cliente_id, ip, valor, status)
        VALUES (1, %s, %s, 'pendente')
    """, (ip, valor))

    conn.commit()
    cur.close()
    conn.close()

@app.route('/compra', methods=['POST'])
def compra():
    data = request.json

    ip = data['ip']
    valor = data['valor']

    salvar_pedido(ip, valor)

    return jsonify({"status": "recebido", "fraude": "em_analise"})

@app.route("/")
def home():
    return "API Cozinet rodando"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
