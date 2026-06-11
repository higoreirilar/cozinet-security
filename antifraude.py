import os
import psycopg2

def get_conn():
    return psycopg2.connect(
        dbname=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        host=os.getenv("PGHOST"),
        port=os.getenv("PGPORT")
    )

def ip_bloqueado(ip):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT 1
        FROM ips_bloqueados
        WHERE ip=%s
        LIMIT 1
    """, (ip,))

    existe = cur.fetchone()

    cur.close()
    conn.close()

    return existe is not None

def calcular_score(ip, valor):

    score = 0
    motivos = []

    # IP bloqueado manualmente
    if ip_bloqueado(ip):
        return 100, ["ip_bloqueado"]

    # valor alto
    if float(valor) > 5000:
        score += 40
        motivos.append("valor_alto")

    # ip inválido
    if ip is None or ip == "0.0.0.0":
        score += 30
        motivos.append("ip_suspeito")

    # valor extremo
    if float(valor) > 10000:
        score += 30
        motivos.append("valor_extremo")

    return min(score, 100), motivos
