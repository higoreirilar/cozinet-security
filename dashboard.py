@app.route("/dashboard")
def dashboard():

    if not login_required():
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor()

    # ---------------- STATS ----------------
    cur.execute("SELECT COUNT(*) FROM pedidos WHERE status='aprovado'")
    aprovados = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM pedidos WHERE status='analise'")
    analise = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM pedidos WHERE status='bloqueado'")
    bloqueados = cur.fetchone()[0]

    # ---------------- PEDIDOS ----------------
    cur.execute("""
        SELECT id, order_id, ip, valor, status, motivo, created_at
        FROM pedidos
        ORDER BY id DESC
        LIMIT 50
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    pedidos = [
        {
            "id": r[0],
            "order_id": r[1],
            "ip": r[2],
            "valor": float(r[3]) if r[3] else 0,
            "status": r[4],
            "motivo": r[5],
            "created_at": str(r[6])
        }
        for r in rows
    ]

    return render_template(
        "dashboard.html",
        aprovados=aprovados,
        analise=analise,
        bloqueados=bloqueados,
        pedidos=pedidos,
        usuario=session.get("nome")
    )
