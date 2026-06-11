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
        SELECT 1 FROM ips_bloqueados WHERE ip=%s LIMIT 1
    """, (ip,))

    existe = cur.fetchone()

    cur.close()
    conn.close()

    return existe is not None


def count_ip_requests(ip):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM pedidos
        WHERE ip=%s
    """, (ip,))

    total = cur.fetchone()[0]

    cur.close()
    conn.close()

    return total


def calcular_score(ip, valor, cpf=None, email=None):

    score = 0
    motivos = []

    # 1. IP já bloqueado
    if ip_bloqueado(ip):
        return 100, ["ip_bloqueado"]

    # 2. muitos pedidos do mesmo IP
    if count_ip_requests(ip) > 20:
        score += 40
        motivos.append("muitos_pedidos_ip")

    # 3. valor alto
    if float(valor) > 5000:
        score += 30
        motivos.append("valor_alto")

    # 4. valor extremo
    if float(valor) > 10000:
        score += 30
        motivos.append("valor_extremo")

    # 5. IP inválido
    if not ip or ip == "0.0.0.0":
        score += 30
        motivos.append("ip_invalido")

    return min(score, 100), motivos


def should_block(score, motivos):
    return score >= 80
