def calcular_score(ip, valor):

    score = 0
    motivos = []

    # valor alto
    if float(valor) > 5000:
        score += 40
        motivos.append("valor_alto")

    # ip inválido
    if ip is None or ip == "0.0.0.0":
        score += 30
        motivos.append("ip_suspeito")

    # padrão simples extra
    if float(valor) > 10000:
        score += 30
        motivos.append("valor_extremo")

    return min(score, 100), motivos
