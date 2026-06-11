from flask import Flask, request, jsonify, render_template, session, redirect
import os
import psycopg2

app = Flask(__name__)
app.secret_key = "cozinet_saas_2026"

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

        cur.execute(
            "SELECT id,nome,role FROM usuarios WHERE email=%s AND senha=%s",
            (email, senha)
        )

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

    cur.execute("SELECT COALESCE(SUM(valor),0) FROM pedidos WHERE status='bloqueado'")
    valor_protegido = float(cur.fetchone()[0] or 0)

    cur.execute("SELECT COALESCE(ROUND(AVG(score_risco),2),0) FROM pedidos")
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

@app.route("/bloqueados")
def bloqueados():
    if not login_required():
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id,ip,motivo,data_bloqueio FROM ips_bloqueados ORDER BY data_bloqueio DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    bloqueados = [{"id":r[0],"ip":r[1],"motivo":r[2],"data":str(r[3])} for r in rows]

    return render_template("bloqueados.html", bloqueados=bloqueados, usuario=session.get("nome"))

@app.route("/ips-confiaveis")
def ips_confiaveis():
    if not login_required():
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id,ip,observacao,data_cadastro FROM ips_confiaveis ORDER BY data_cadastro DESC")
    dados = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("ips_confiaveis.html", dados=dados, usuario=session.get("nome"))

@app.route("/logs")
def logs():
    if not login_required():
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT usuario,acao,detalhe,created_at FROM logs_antifraude ORDER BY created_at DESC LIMIT 300")
    logs = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("logs.html", logs=logs, usuario=session.get("nome"))

@app.route("/bloquear-ip", methods=["POST"])
def bloquear_ip():
    if not login_required():
        return jsonify({"error":"unauthorized"}), 401

    dados = request.get_json()
    ip = dados.get("ip")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO ips_bloqueados(ip,motivo)
        VALUES(%s,%s)
        ON CONFLICT(ip) DO NOTHING
    """, (ip, "Bloqueio manual"))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"success":True, "message":f"IP {ip} bloqueado"})

@app.route("/desbloquear-ip/<int:id>", methods=["POST"])
def desbloquear_ip(id):
    if not login_required():
        return jsonify({"error":"unauthorized"}), 401

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM ips_bloqueados WHERE id=%s", (id,))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"success":True, "message":"IP desbloqueado com sucesso"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
