def check_fraude(ip, valor):

    # regras simples iniciais (você pode evoluir depois)

    if ip is None:
        return {"fraude": True, "motivo": "sem_ip"}

    if float(valor) > 10000:
        return {"fraude": True, "motivo": "valor_suspeito"}

    if ip == "127.0.0.1":
        return {"fraude": True, "motivo": "ip_local"}

    return {"fraude": False, "motivo": "ok"}
