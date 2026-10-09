from backend.importacao.csv_pedidos import ArquivoInvalido, ler_pedidos
from backend.importacao.historico_compras import main

CABECALHO = '"Local";"Numero do Pedido";"Data do Pedido";"Solicitante";"Fornecedor";"Item do Pedido";"Grupo do Item";"Quatidade UN";"Valor Unitario";"Valor Total";"Previsao de Entrega";"Status do Pedido";"Condicao de Pgto";"Observacao";"Aprovador";"Data de Aprovacao"'

CSV = CABECALHO + '''
"MAIS TELECOMUNICACOES LTDA";"3738";"18/02/2026";"ANA COMPRAS";"PB MATERIAIS ELÉTRICOS, HIDRÁULICOS LTDA";"ELETRODUTO PVC 1"";"Estoque";"400";"8,41";"3365,40";"";"Recebido";"A Prazo 2X";"1. Identificação
Solicitante: Operacional

- linha com ; ponto e vírgula";"BRUNO APROVA";""
"MAIS TELECOMUNICACOES LTDA";"3738";"18/02/2026";"ANA COMPRAS";"PB MATERIAIS ELÉTRICOS, HIDRÁULICOS LTDA";"CAIXA ÓPTICA";"Produtos Diversos";"2";"50,00";"100,00";"";"Recebido";"A Prazo 2X";"";"BRUNO APROVA";""
"MAIS INTERNET LTDA";"3801";"02/03/2026";"ANA COMPRAS";"LOJA X";"ELETRODUTO PVC 1"";"Estoque";"100";"8,50";"850,00";"10/03/2026 00:00:00";"Recebido";"A Prazo 1X (28 dias)";"";"BRUNO APROVA";"02/03/2026"
'''


def test_leitor_aceita_aspas_sem_escape_e_textos_com_quebra_de_linha():
    registros, problemas = ler_pedidos(CSV)

    assert problemas == []
    assert len(registros) == 3
    assert registros[0]["Item do Pedido"] == 'ELETRODUTO PVC 1"'
    assert registros[0]["Grupo do Item"] == "Estoque"
    assert "ponto e vírgula" in registros[0]["Observacao"]


def test_leitor_recusa_outro_arquivo():
    try:
        ler_pedidos('"Codigo";"Nome"\n"1";"x"\n')
    except ArquivoInvalido as erro:
        assert "Itens do Pedido de Compra" in str(erro)
    else:
        raise AssertionError("deveria recusar")


def test_importa_historico(cliente_autenticado, tmp_path):
    arquivo = tmp_path / "pedidos.csv"
    arquivo.write_text(CSV, encoding="utf-8")

    assert main([str(arquivo), "--email", "usuario.testes@teste.com", "--senha", "senha123", "--forcar", "--estoque-minimo"]) == 0

    solicitacoes = cliente_autenticado.get("/solicitacoes-compra").json()
    assert len(solicitacoes) == 2
    assert {s["status"] for s in solicitacoes} == {"RECEBIDA"}
    assert {s["solicitante"] for s in solicitacoes} == {"Ana Compras"}

    compras = cliente_autenticado.get("/compras").json()
    assert sorted(round(c["valor_total"], 2) for c in compras) == [850.0, 3465.4]

    produtos = {p["nome"]: p for p in cliente_autenticado.get("/produtos", params={"tamanho": 100}).json()}
    assert produtos['ELETRODUTO PVC 1"']["quantidade"] == 500
    assert produtos['ELETRODUTO PVC 1"']["estoque_minimo"] > 0
    assert produtos["CAIXA ÓPTICA"]["estoque_minimo"] == 0

    usuarios = {u["nome"]: u for u in cliente_autenticado.get("/usuarios").json()}
    assert usuarios["Bruno Aprova"]["ativo"] is False
    assert usuarios["Bruno Aprova"]["perfil"] == "APROVADOR"

    movimentos = cliente_autenticado.get("/movimentacoes").json()
    assert {m["data_movimentacao"][:10] for m in movimentos} == {"2026-02-25", "2026-03-10"}

    formas = [f["titulo"] for f in cliente_autenticado.get("/formas-pagamento?tamanho=100").json()["itens"]]
    assert "A Prazo 1X (28 dias)" in formas


def test_nao_importa_em_banco_com_dados_sem_forcar(cliente_autenticado, tmp_path):
    arquivo = tmp_path / "pedidos.csv"
    arquivo.write_text(CSV, encoding="utf-8")
    assert main([str(arquivo), "--email", "usuario.testes@teste.com", "--senha", "senha123", "--forcar"]) == 0

    try:
        main([str(arquivo), "--email", "usuario.testes@teste.com", "--senha", "senha123"])
    except SystemExit as erro:
        assert "já tem" in str(erro)
    else:
        raise AssertionError("deveria recusar")


def test_importacao_continua_quando_o_login_vence(cliente_autenticado, tmp_path, monkeypatch):
    """Em PCs lentos a importação passa dos 30 minutos do login."""
    from datetime import datetime, timedelta, timezone

    from jose import jwt

    import backend.autenticacao as autenticacao
    import backend.routes.usuarios as rotas_usuarios

    def token_vencido(usuario_id, email):
        dados = {"sub": str(usuario_id), "email": email, "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}
        return jwt.encode(dados, autenticacao.CHAVE_SECRETA, algorithm=autenticacao.ALGORITMO)

    monkeypatch.setattr(rotas_usuarios, "criar_token_acesso", token_vencido)
    arquivo = tmp_path / "pedidos.csv"
    arquivo.write_text(CSV, encoding="utf-8")

    assert main([str(arquivo), "--email", "usuario.testes@teste.com", "--senha", "senha123", "--forcar",
                 "--estoque-minimo", "--simular-consumo"]) == 0

    solicitacoes = cliente_autenticado.get("/solicitacoes-compra").json()
    assert {s["status"] for s in solicitacoes} == {"RECEBIDA"} and len(solicitacoes) == 2


def test_desfazer_e_importar_de_novo(cliente_autenticado, tmp_path):
    arquivo = tmp_path / "pedidos.csv"
    arquivo.write_text(CSV, encoding="utf-8")
    argumentos = [str(arquivo), "--email", "usuario.testes@teste.com", "--senha", "senha123", "--forcar"]

    def estoque():
        produtos = cliente_autenticado.get("/produtos", params={"tamanho": 100}).json()
        return {p["nome"]: p["quantidade"] for p in produtos}

    assert main(argumentos + ["--simular-consumo"]) == 0
    manual = cliente_autenticado.post("/movimentacoes", json={
        "produto_id": next(p["id"] for p in cliente_autenticado.get("/produtos").json() if p["nome"] == "CAIXA ÓPTICA"),
        "tipo": "ENTRADA", "quantidade": 3,
    })
    assert manual.status_code == 201

    assert main(argumentos + ["--desfazer", "--simular-consumo"]) == 0
    solicitacoes = cliente_autenticado.get("/solicitacoes-compra").json()
    assert len(solicitacoes) == 2
    assert {s["solicitante"] for s in solicitacoes} == {"Ana Compras"}
    usuarios = [u for u in cliente_autenticado.get("/usuarios").json() if u["nome"] == "Ana Compras"]
    assert len(usuarios) == 1 and usuarios[0]["ativo"] is False

    assert main(argumentos + ["--so-desfazer"]) == 0
    assert cliente_autenticado.get("/solicitacoes-compra").json() == []
    assert estoque() == {'ELETRODUTO PVC 1"': 0, "CAIXA ÓPTICA": 3}
    movimentos = cliente_autenticado.get("/movimentacoes").json()
    assert [(m["tipo"], m["quantidade"]) for m in movimentos] == [("ENTRADA", 3)]
