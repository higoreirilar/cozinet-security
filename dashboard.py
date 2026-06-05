from flask import Flask, render_template_string
import psycopg2

app = Flask(__name__)

HTML = """
<h1>📊 PAINEL ANTIFRAUDE</h1>
<table border="1" cellpadding="5">
<tr>
<th>ID</th>
<th>IP</th>
<th>Valor</th>
<th>Status</th>
</tr>
{% for row in data %}
<tr>
<td>{{row[0]}}</td>
<td>{{row[1]}}</td>
<td>{{row[2]}}</td>
<td>{{row[3]}}</td>
</tr>
{% endfor %}
</table>
"""

def get_data():
    conn = psycopg2.connect(
        dbname="loja",
        user="postgres",
        password="@32426022",
        host="localhost",
        port="5432"
    )

    cur = conn.cursor()
    cur.execute("SELECT id, ip, valor, status FROM pedidos ORDER BY id DESC")
    data = cur.fetchall()

    cur.close()
    conn.close()

    return data

@app.route("/")
def home():
    data = get_data()
    return render_template_string(HTML, data=data)

if __name__ == "__main__":
    app.run(port=5001, debug=True)
