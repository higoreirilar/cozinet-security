@dashboard.route("/dashboard")
def dashboard_data():

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM pedidos
        WHERE status='aprovado'
    """)
    aprovados = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM pedidos
        WHERE status='analise'
    """)
    analise = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM pedidos
        WHERE status='bloqueado'
    """)
    bloqueados = cur.fetchone()[0]

    cur.execute("""
        SELECT
            id,
            order_id,
            ip,
            valor,
            status,
            motivos,
            created_at
        FROM pedidos
        ORDER BY id DESC
        LIMIT 50
    """)

    pedidos = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify({
        "aprovados": aprovados,
        "analise": analise,
        "bloqueados": bloqueados,
        "pedidos": pedidos
    })
