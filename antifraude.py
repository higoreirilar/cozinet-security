import psycopg2

conn = psycopg2.connect(
    dbname="loja",
    user="postgres",
    password="SUA_SENHA_AQUI",
    host="localhost",
    port="5432"
)

cur = conn.cursor()

cur.execute("""
SELECT ip,
       COUNT(*) AS compras,
       SUM(valor) AS total
FROM pedidos
GROUP BY ip;
""")

dados = cur.fetchall()

print("\n🧠 SCORE DE FRAUDE:\n")

for ip, compras, total in dados:

    score = 0

    # regra 1: muitas compras
    if compras >= 3:
        score += 50

    # regra 2: valor alto
    if total > 500:
        score += 40

    # regra 3: risco mínimo base
    if compras == 1:
        score += 10

    print(f"IP: {ip}")
    print(f"Compras: {compras}")
    print(f"Total: R${total}")
    print(f"🚨 Score de risco: {score}/100")
    print("-" * 30)

cur.close()
conn.close()
