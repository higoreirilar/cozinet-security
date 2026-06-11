from flask import Flask, render_template, request, redirect, session, jsonify
import psycopg2
import os

app = Flask(__name__)
app.secret_key = "secret-key-change"

# =========================
# DATABASE
# =========================
def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT", 5432)
    )


# =========================
# LOGIN
# =========================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        senha = request.form["senha"]

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id, nome FROM usuarios WHERE email=%s AND senha=%s", (email, senha))
        user = cur.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["user"] = user[1]
            return redirect("/dashboard")

        return "Login inválido"

    return render_template("login.html")


# =========================
# DASHBOARD
# =========================
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/")

    conn = get_conn()
    cur = conn.cursor()

    # pedidos
    cur.execute("""
        SELECT id, order_id, cliente, cpf, email, telefone, ip,
               valor, score_risco, status
        FROM pedidos
        ORDER BY id DESC
    """)
    rows = cur.fetchall()

    pedidos = [
        {
            "id": r[0],
            "order_id": r[1],
            "cliente": r[2],
            "cpf": r[3],
            "email": r[4],
            "telefone": r[5],
            "ip": r[6],
            "valor": float(r[7]) if r[7] else 0,
            "score_risco": r[8],
            "status": r[9]
        }
        for r in rows
    ]

    # KPIs
    cur.execute("SELECT COUNT(*) FROM pedidos")
    total_pedidos = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM pedidos WHERE status='aprovado'")
    aprovados = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM pedidos WHERE status='analise'")
    analise = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM pedidos WHERE status='bloqueado'")
    bloqueados = cur.fetchone()[0]

    cur.execute("SELECT COALESCE(SUM(valor),0) FROM pedidos WHERE status='aprovado'")
    valor_protegido = cur.fetchone()[0]

    cur.execute("SELECT COALESCE(AVG(score_risco),0) FROM pedidos")
    score_medio = round(cur.fetchone()[0], 2)

    conn.close()

    return render_template(
        "dashboard.html",
        usuario=session.get("user"),
        pedidos=pedidos,
        total_pedidos=total_pedidos,
        aprovados=aprovados,
        analise=analise,
        bloqueados=bloqueados,
        valor_protegido=valor_protegido,
        score_medio=score_medio
    )


# =========================
# BLOQUEAR IP
# =========================
@app.route("/bloquear-ip", methods=["POST"])
def bloquear_ip():
    data = request.get_json()
    ip = data["ip"]

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO ips_bloqueados (ip, motivo, data_bloqueio)
        VALUES (%s, %s, NOW())
        ON CONFLICT DO NOTHING
    """, (ip, "manual"))

    cur.execute("""
        UPDATE pedidos SET status='bloqueado' WHERE ip=%s
    """, (ip,))

    conn.commit()
    conn.close()

    return jsonify({"ok": True})


# =========================
# DESBLOQUEAR IP
# =========================
@app.route("/desbloquear-ip", methods=["POST"])
def desbloquear_ip():
    data = request.get_json()
    ip = data["ip"]

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM ips_bloqueados WHERE ip=%s", (ip,))
    cur.execute("UPDATE pedidos SET status='analise' WHERE ip=%s", (ip,))

    conn.commit()
    conn.close()

    return jsonify({"ok": True})


# =========================
# LOGS
# =========================
@app.route("/logs")
def logs():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, ip, acao, created_at, detalhes
        FROM logs
        ORDER BY id DESC
        LIMIT 200
    """)

    logs = cur.fetchall()
    conn.close()

    return render_template("logs.html", logs=logs)


# =========================
# BLOQUEADOS
# =========================
@app.route("/bloqueados")
def bloqueados():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT ip, motivo, data_bloqueio
        FROM ips_bloqueados
        ORDER BY data_bloqueio DESC
    """)

    data = cur.fetchall()
    conn.close()

    return render_template("bloqueados.html", ips=data)


# =========================
# CONFIÁVEIS
# =========================
@app.route("/ips-confiaveis")
def confiaveis():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT ip, observacao, data_cadastro
        FROM ips_confiaveis
        ORDER BY data_cadastro DESC
    """)

    data = cur.fetchall()
    conn.close()

    return render_template("ips_confiaveis.html", ips=data)


# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
