from flask import render_template, session, redirect
from app import app, get_conn, login_required


@app.route("/dashboard")
def dashboard():

    if not login_required():
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor()

    # TOTAL PEDIDOS
    cur.execute("SELECT COUNT(*) FROM pedidos")
    total_pedidos = cur.fetchone()[0]

    # APROVADOS
    cur.execute("""
        SELECT COUNT(*)
        FROM pedidos
        WHERE status='aprovado'
    """)
    aprovados = cur.fetchone()[0]

    # ANALISE
    cur.execute("""
        SELECT COUNT(*)
        FROM pedidos
        WHERE status='analise'
    """)
    analise = cur.fetchone()[0]

    # BLOQUEADOS
    cur.execute("""
        SELECT COUNT(*)
        FROM pedidos
        WHERE status='bloqueado'
    """)
    bloqueados = cur.fetchone()[0]

    # VALOR PROTEGIDO
    cur.execute("""
        SELECT COALESCE(SUM(valor),0)
        FROM pedidos
        WHERE status='bloqueado'
    """)
    valor_protegido = float(cur.fetchone()[0] or 0)

    # SCORE MÉDIO
    cur.execute("""
        SELECT COALESCE(ROUND(AVG(score_risco),2),0)
        FROM pedidos
    """)
    score_medio = cur.fetchone()[0]

    # PEDIDOS
    cur.execute("""
        SELECT
            id,
            order_id,
            cliente,
            cpf,
            email,
            cidade,
            estado,
            ip,
            dispositivo,
            valor,
            score_risco,
            status,
            motivo,
            created_at,
            analisado_por,
            data_analise,
            pais
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
