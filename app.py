from flask import Flask, request, jsonify, render_template, session, redirect
import os
import psycopg2

app = Flask(__name__)
app.secret_key = "cozinet_saas_2026"


# =========================
# DATABASE CONNECTION
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
# LOGIN CHECK
# =========================
def login_required():
    return "user_id" in session


# =========================
# ROUTES
# =========================

@app.route("/")
def home():
    return redirect("/login")


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

    cur.execute("SELECT COUNT(*) FROM pedidos")
    total_pedidos = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM pedidos WHERE status='aprovado'")
    aprovados = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM pedidos WHERE status='analise'")
    analise = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM pedidos WHERE status='bloqueado'")
    bloqueados = cur.fetchone()[0]

    cur.execute("""
        SELECT COALESCE(SUM(valor),0)
        FROM pedidos
        WHERE status='bloqueado'
    """)
    valor_protegido = float(cur.fetchone()[0] or 0)

    cur.execute("""
        SELECT COALESCE(ROUND(AVG(score_risco),2),0)
        FROM pedidos
    """)
    score_medio = cur.fetchone()[0]

    cur.execute("""
        SELECT id,order_id,cliente,cpf,email,cidade,estado,
               ip,dispositivo,valor,score_risco,status,
               motivo,created_at,analisado_por,data_analise,pais
        FROM pedidos
        ORDER BY id DESC
        LIMIT 100
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
            "cidade": r[5],
            "estado": r[6],
            "ip": r[7],
            "dispositivo": r[8],
            "valor": float(r[9]) if r[9] else 0,
            "score_risco": r[10] if r[10] else 0,
            "status": r[11],
            "motivo": r[12],
            "created_at": str(r[13]) if r[13] else "",
            "analisado_por": r[14],
            "data_analise": str(r[15]) if r[15] else "",
            "pais": r[16]
        })

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

    dados = request.get_json()
    ip = dados.get("ip")

    conn = get_conn()
    cur = conn.cursor()

    # bloqueia IP
    cur.execute("""
        INSERT INTO ips_bloqueados(ip, motivo)
        VALUES(%s,%s)
        ON CONFLICT(ip) DO NOTHING
    """, (ip, "Bloqueio manual"))

    # também atualiza pedidos com esse IP
    cur.execute("""
        UPDATE pedidos
        SET status='bloqueado'
        WHERE ip=%s
    """, (ip,))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"success": True, "message": f"IP {ip} bloqueado"})


# =========================
# DESBLOQUEAR IP
# =========================
@app.route("/desbloquear-ip/<int:id>", methods=["POST"])
def desbloquear_ip(id):

    if not login_required():
        return jsonify({"error": "unauthorized"}), 401

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM ips_bloqueados WHERE id=%s", (id,))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"success": True, "message": "IP desbloqueado"})


# =========================
# MUDAR STATUS PEDIDO (NOVO)
# =========================
@app.route("/mudar-status-pedido", methods=["POST"])
def mudar_status_pedido():

    if not login_required():
        return jsonify({"error": "unauthorized"}), 401

    dados = request.get_json()

    pedido_id = dados.get("id")
    status = dados.get("status")

    conn = get_conn()
    cur = conn.cursor()

    # atualiza status do pedido
    cur.execute("""
        UPDATE pedidos
        SET status=%s
        WHERE id=%s
    """, (status, pedido_id))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"success": True, "message": "Status atualizado"})


# =========================
# RUN APP
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
