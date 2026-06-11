from flask import Flask, request, jsonify, render_template, session, redirect
import os
import psycopg2

app = Flask(__name__)
app.secret_key = "cozinet_saas_2026"


# =========================
# DB
# =========================
def get_conn():
    return psycopg2.connect(
        dbname=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        host=os.getenv("PGHOST"),
        port=os.getenv("PGPORT")
    )


def login_required():
    return "user_id" in session


# =========================
# LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        email = request.form.get("email")
        senha = request.form.get("senha")

        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, nome, role
            FROM usuarios
            WHERE email=%s AND senha=%s
        """, (email, senha))

        user = cur.fetchone()

        cur.close()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["nome"] = user[1]
            session["role"] = user[2]
            return redirect("/dashboard")

        return render_template("login.html", erro="Login inválido")

    return render_template("login.html")


# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# =========================
# DASHBOARD
# =========================
@app.route("/dashboard")
def dashboard():

    if not login_required():
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor()

    # KPIs
    cur.execute("SELECT COUNT(*) FROM pedidos")
    total_pedidos = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM pedidos WHERE status='aprovado'")
    aprovados = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM pedidos WHERE status='analise'")
    analise = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM pedidos p
        JOIN ips_bloqueados b ON b.ip = p.ip
    """)
    bloqueados = cur.fetchone()[0]

    cur.execute("""
        SELECT COALESCE(SUM(p.valor),0)
        FROM pedidos p
        JOIN ips_bloqueados b ON b.ip = p.ip
    """)
    valor_protegido = float(cur.fetchone()[0] or 0)

    cur.execute("""
        SELECT COALESCE(ROUND(AVG(score_risco),2),0)
        FROM pedidos
    """)
    score_medio = cur.fetchone()[0]

    # PEDIDOS COMPLETO
    cur.execute("""
        SELECT id, order_id, cliente, cpf, email,
               telefone, rua, cep,
               cidade, estado,
               ip, valor, score_risco,
               status, motivo, created_at
        FROM pedidos
        ORDER BY id DESC
        LIMIT 100
    """)

    rows = cur.fetchall()

    pedidos = []

    for r in rows:

        cpf = r[3]
        ip = r[10]

        # histórico CPF
        cur.execute("""
            SELECT order_id, valor, status, created_at
            FROM pedidos
            WHERE cpf=%s
            ORDER BY id DESC
            LIMIT 5
        """, (cpf,))
        hist_cpf = cur.fetchall()

        # histórico IP
        cur.execute("""
            SELECT order_id, cliente, valor, status, created_at
            FROM pedidos
            WHERE ip=%s
            ORDER BY id DESC
            LIMIT 5
        """, (ip,))
        hist_ip = cur.fetchall()

        pedidos.append({
            "id": r[0],
            "order_id": r[1],
            "cliente": r[2],
            "cpf": r[3],
            "email": r[4],

            "telefone": r[5],
            "rua": r[6],
            "cep": r[7],
            "cidade": r[8],
            "estado": r[9],

            "ip": r[10],
            "valor": float(r[11] or 0),
            "score_risco": r[12],
            "status": r[13],
            "motivo": r[14],
            "created_at": str(r[15]),

            "hist_cpf": hist_cpf,
            "hist_ip": hist_ip
        })

    cur.close()
    conn.close()

    return render_template(
        "dashboard.html",
        usuario=session.get("nome"),
        total_pedidos=total_pedidos,
        aprovados=aprovados,
        analise=analise,
        bloqueados=bloqueados,
        valor_protegido=valor_protegido,
        score_medio=score_medio,
        pedidos=pedidos
    )


# =========================
# BLOQUEAR IP
# =========================
@app.route("/bloquear-ip", methods=["POST"])
def bloquear_ip():

    if not login_required():
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json()
    ip = data.get("ip")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO ips_bloqueados(ip, motivo)
        VALUES(%s,%s)
        ON CONFLICT(ip) DO NOTHING
    """, (ip, "manual"))

    cur.execute("""
        UPDATE pedidos
        SET status='bloqueado'
        WHERE ip=%s
    """, (ip,))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "bloqueado"})


# =========================
# DESBLOQUEAR IP
# =========================
@app.route("/desbloquear-ip", methods=["POST"])
def desbloquear_ip():

    if not login_required():
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json()
    ip = data.get("ip")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM ips_bloqueados WHERE ip=%s", (ip,))

    cur.execute("""
        UPDATE pedidos
        SET status='analise'
        WHERE ip=%s
    """, (ip,))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "desbloqueado"})


# =========================
# BLOQUEADOS
# =========================
@app.route("/bloqueados")
def bloqueados():

    if not login_required():
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, ip, motivo, data_cadastro
        FROM ips_bloqueados
        ORDER BY id DESC
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("bloqueados.html", bloqueados=rows)


# =========================
# CONFIÁVEIS
# =========================
@app.route("/ips-confiaveis")
def confiaveis():

    if not login_required():
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, ip, observacao, data_cadastro
        FROM ips_confiaveis
        ORDER BY id DESC
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("ips_confiaveis.html", ips=rows)


# =========================
# LOGS
# =========================
@app.route("/logs")
def logs():

    if not login_required():
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, ip, acao, detalhes, created_at
        FROM logs
        ORDER BY id DESC
        LIMIT 200
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("logs.html", logs=rows)


# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
