<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cozinet SaaS Dashboard</title>

<style>
body {
    margin: 0;
    font-family: Arial;
    background: #0a0a0a;
    color: white;
    display: flex;
}

/* SIDEBAR */
.sidebar {
    width: 240px;
    background: #111214;
    height: 100vh;
    padding: 18px;
    border-right: 1px solid #222;
}

.logo img {
    width: 150px;
}

.logo h2 {
    font-size: 13px;
    color: #ff6a00;
    margin-top: 10px;
    text-align: center;
}

/* MENU */
.menu div {
    padding: 10px;
    cursor: pointer;
    border-radius: 6px;
    color: #aaa;
}

.menu div:hover {
    background: #1c1c1f;
    color: #ff6a00;
}

/* MAIN */
.main {
    flex: 1;
    padding: 20px;
}

/* TOP */
.topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15px;
}

.title {
    font-size: 18px;
    color: #ff6a00;
}

/* CARDS PREMIUM */
.cards {
    display: flex;
    gap: 12px;
}

.card {
    width: 180px;
    padding: 12px;
    border-radius: 12px;
    color: white;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}

.card h3 {
    margin: 0;
    font-size: 18px;
}

.card p {
    margin: 5px 0 0;
    font-size: 11px;
    opacity: 0.8;
}

/* CORES MAIS BONITAS */
.green {
    background: linear-gradient(135deg, #16a34a, #22c55e);
}

.yellow {
    background: linear-gradient(135deg, #f59e0b, #fbbf24);
}

.red {
    background: linear-gradient(135deg, #dc2626, #ef4444);
}

/* TABELA */
table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 15px;
    background: #15161a;
    border-radius: 10px;
    overflow: hidden;
    font-size: 13px;
}

th {
    background: #111214;
    color: #ff6a00;
    padding: 10px;
    text-align: left;
}

td {
    padding: 10px;
    border-bottom: 1px solid #222;
}

tr:hover {
    background: #1c1c1f;
}

/* STATUS */
.aprovado { color: #22c55e; font-weight: bold; }
.analise { color: #fbbf24; font-weight: bold; }
.bloqueado { color: #ef4444; font-weight: bold; }
</style>
</head>

<body>

<!-- SIDEBAR -->
<div class="sidebar">

    <div class="logo">
        <img src="https://i.ibb.co/p6D813mT/Cozinet-1.png">
        <h2>Cozinet Antifraude</h2>
    </div>

    <div class="menu">
        <div>📊 Dashboard</div>
        <div>🧾 Pedidos</div>
        <div>🚨 Fraudes</div>
        <div>⚙️ Configurações</div>
    </div>

</div>

<!-- MAIN -->
<div class="main">

    <div class="topbar">
        <div class="title">Dashboard de Monitoramento</div>
    </div>

    <!-- CARDS BONITOS -->
    <div class="cards">

        <div class="card green">
            <h3 id="aprovados">0</h3>
            <p>Pedidos aprovados sem risco identificado</p>
        </div>

        <div class="card yellow">
            <h3 id="analise">0</h3>
            <p>Pedidos em análise de segurança</p>
        </div>

        <div class="card red">
            <h3 id="bloqueados">0</h3>
            <p>Transações bloqueadas por risco</p>
        </div>

    </div>

    <!-- TABELA -->
    <table>
        <tr>
            <th>ID</th>
            <th>Pedido</th>
            <th>IP</th>
            <th>Valor</th>
            <th>Status</th>
            <th>Motivos</th>
            <th>Data</th>
        </tr>

        <tbody id="tabela"></tbody>
    </table>

</div>

<script>
async function atualizar(){
    const res = await fetch("/dashboard");
    const dados = await res.json();

    let a=0,b=0,c=0;
    let html="";

    dados.forEach(d=>{

        if(d.status==="aprovado") a++;
        if(d.status==="analise") b++;
        if(d.status==="bloqueado") c++;

        html += `
        <tr>
            <td>${d.id}</td>
            <td>${d.order_id}</td>
            <td>${d.ip}</td>
            <td>R$ ${d.valor}</td>
            <td class="${d.status}">${d.status}</td>
            <td>${d.motivos}</td>
            <td>${d.created_at}</td>
        </tr>`;
    });

    document.getElementById("tabela").innerHTML = html;
    document.getElementById("aprovados").innerText = a;
    document.getElementById("analise").innerText = b;
    document.getElementById("bloqueados").innerText = c;
}

setInterval(atualizar,3000);
atualizar();
</script>

</body>
</html>
