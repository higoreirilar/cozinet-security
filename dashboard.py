from flask import Flask, jsonify
import os
import psycopg2

dashboard = Flask(__name__)

def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])

@dashboard.route("/pedidos")
def pedidos():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM pedidos")
    dados = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify(dados)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    dashboard.run(host="0.0.0.0", port=port)
