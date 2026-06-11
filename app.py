from flask import Flask, render_template, request, jsonify, redirect, session
import os
import psycopg2
import time

app = Flask(__name__)
app.secret_key = "eirilar_shield_2026"

START_TIME = time.time()

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

# =========================
# AUTH
# =========================
def login_required():
    return "user_id" in session

# =========================
# SYSTEM INFO (evita erro do dashboard)
# =========================
def get_system():
    return {
        "status": "online",
        "host": request.host,
        "uptime": int(time.time() - START_TIME),
        "hostname": os.getenv("HOSTNAME", "server"),
        "port": 8080,
        "env": "production"
    }

# =========================
# LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        senha = request.form["senha"]

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
# DASHBOARD
# =========================
@app.route("/dashboard")
def dashboard():
    if not login_required():
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM pedidos")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM pedidos WHERE status='aprovado'")
    aprovados = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM pedidos WHERE status='analise'")
    analise = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM pedidos WHERE status='bloqueado'")
    bloqueados = cur.fetchone()[0]

    cur.execute("""
        SELECT id, order_id, cliente, cpf, email, telefone,
               rua, bairro, cidade, estado, pais, cep,
               ip, valor, score_risco, status, motivo, created_at
        FROM pedidos
        ORDER BY id DESC
        LIMIT 80
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    pedidos = []
    for r in rows:
        pedidos.append({
            "id": r[0],
            "order_id": r[1],
            "cliente": r[2],
            "cpf": r[3],
            "email": r[4],
            "telefone": r[5],
            "rua": r[6],
            "bairro": r[7],
            "cidade": r[8],
            "estado": r[9],
            "pais": r[10],
            "cep": r[11],
            "ip": r[12],
            "valor": float(r[13] or 0),
            "score_risco": r[14],
            "status": r[15],
            "motivo": r[16],
            "created_at": str(r[17])
        })

    return render_template(
        "dashboard.html",
        usuario=session.get("nome"),
        system=get_system(),
        total=total,
        aprovados=aprovados,
        analise=analise,
        bloqueados=bloqueados,
        pedidos=pedidos
    )

# =========================
# BLOQUEIO IP
# =========================
@app.route("/bloquear-ip", methods=["POST"])
def bloquear_ip():
    ip = request.json["ip"]

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO ips_bloqueados(ip, motivo, data_cadastro)
        VALUES(%s, %s, NOW())
        ON CONFLICT DO NOTHING
    """, (ip, "manual"))

    cur.execute("""
        UPDATE pedidos SET status='bloqueado'
        WHERE ip=%s
    """, (ip,))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"ok": True})

# =========================
# DESBLOQUEIO
# =========================
@app.route("/desbloquear-ip", methods=["POST"])
def desbloquear_ip():
    ip = request.json["ip"]

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM ips_bloqueados WHERE ip=%s", (ip,))

    cur.execute("""
        UPDATE pedidos SET status='analise'
        WHERE ip=%s
    """, (ip,))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"ok": True})

# =========================
# PÁGINAS
# =========================
@app.route("/bloqueados")
def bloqueados():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, ip, motivo, data_cadastro
        FROM ips_bloqueados
        ORDER BY id DESC
    """)

    dados = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("bloqueados.html", bloqueados=dados)

@app.route("/ips-confiaveis")
def confiaveis():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, ip, observacao, data_cadastro
        FROM ips_confiaveis
        ORDER BY id DESC
    """)

    dados = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("ips_confiaveis.html", ips=dados)

@app.route("/logs")
def logs():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, acao, detalhes, ip, created_at
        FROM logs
        ORDER BY id DESC
        LIMIT 100
    """)

    dados = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("logs.html", logs=dados, usuario=session.get("nome"))

# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
