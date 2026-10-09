from backend.tests.apoio_compras import (
    compra_registrada,
    criar_fornecedor,
    criar_produto,
    novo_cliente,
    registrar_cotacao,
)


def nova_solicitacao(cliente, produto_id):
    resposta = cliente.post(
        "/solicitacoes-compra",
        json={"itens": [{"produto_id": produto_id, "quantidade": 3}]}
    )
    assert resposta.status_code == 201
    return resposta.json()["id"]


def preparar(cliente):
    comprada, compra = compra_registrada(cliente, data_compra="2020-01-01", previsao="2020-01-10")
    cabo = compra["itens"][0]["produto_id"]

    aberta = nova_solicitacao(cliente, cabo)
    em_cotacao = nova_solicitacao(cliente, cabo)
    fornecedor = criar_fornecedor(cliente, "Fornecedor Dois")
    registrar_cotacao(cliente, em_cotacao, fornecedor, {cabo: 3})

    criar_produto(cliente, "Avulso sem pedido")

    return comprada, aberta, em_cotacao


def tipos(resposta):
    return [(n["tipo"], n["link"]) for n in resposta.json()["itens"]]


def test_administrador_ve_todas_as_pendencias(cliente_autenticado):
    comprada, aberta, em_cotacao = preparar(cliente_autenticado)

    resposta = cliente_autenticado.get("/notificacoes")

    assert resposta.status_code == 200
    dados = resposta.json()
    itens = tipos(resposta)
    assert ("cotar", f"#/solicitacoes/{aberta}") in itens
    assert ("aprovar", f"#/solicitacoes/{em_cotacao}") in itens
    assert ("receber", f"#/solicitacoes/{comprada}") in itens
    assert ("repor", "#/sugestoes-compra") in itens
    assert dados["total"] == len(dados["itens"])
    assert all(n["urgente"] for n in dados["itens"][:2])
    assert "atrasada" in next(n for n in dados["itens"] if n["tipo"] == "receber")["titulo"]
    assert "1 produto" in next(n for n in dados["itens"] if n["tipo"] == "repor")["titulo"]


def test_cada_perfil_ve_so_o_que_lhe_cabe(cliente_autenticado):
    comprada, aberta, em_cotacao = preparar(cliente_autenticado)

    almoxarife = {t for t, _ in tipos(novo_cliente("ALMOXARIFE").get("/notificacoes"))}
    aprovador = tipos(novo_cliente("APROVADOR").get("/notificacoes"))
    comprador = {t for t, _ in tipos(novo_cliente("COMPRADOR").get("/notificacoes"))}

    assert almoxarife == {"repor", "receber"}
    assert aprovador == [("aprovar", f"#/solicitacoes/{em_cotacao}")]
    assert comprador == {"repor", "cotar"}
    assert novo_cliente("CONSULTA").get("/notificacoes").json() == {"total": 0, "itens": []}


def test_aprovador_nao_e_avisado_da_propria_solicitacao(cliente_autenticado):
    cabo = criar_produto(cliente_autenticado, "Cabo")
    comprador = novo_cliente("COMPRADOR")
    solicitacao = nova_solicitacao(comprador, cabo)
    fornecedor = criar_fornecedor(cliente_autenticado, "Fornecedor A")
    registrar_cotacao(cliente_autenticado, solicitacao, fornecedor, {cabo: 1})

    from backend.database import conectar
    usuario_id = comprador.get("/usuarios/me").json()["id"]
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("UPDATE usuarios SET perfil = 'APROVADOR' WHERE id = %s;", (usuario_id,))
    conexao.commit()
    conexao.close()

    assert comprador.get("/notificacoes").json()["itens"] == []
