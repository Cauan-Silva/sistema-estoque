from backend.tests.apoio_compras import (
    compra_registrada,
    solicitacao_aprovada,
)


def receber(cliente, solicitacao_id, **dados):
    return cliente.post(
        f"/solicitacoes-compra/{solicitacao_id}/compra/recebimentos",
        json=dados
    )


def estoque(cliente, produto_id):
    return cliente.get(f"/produtos/{produto_id}").json()["quantidade"]


def test_receber_tudo_atualiza_estoque(cliente_autenticado):
    cliente = cliente_autenticado
    solicitacao_id, compra = compra_registrada(cliente)
    cabo, conector = (item["produto_id"] for item in compra["itens"])

    assert compra["situacao_recebimento"] == "PENDENTE"

    resposta = receber(
        cliente,
        solicitacao_id,
        data_recebimento="2026-10-05",
        nota_fiscal="NF-123"
    )

    assert resposta.status_code == 201

    dados = resposta.json()

    assert dados["nota_fiscal"] == "NF-123"
    assert dados["recebedor"] == "Usuario Testes"
    assert [(i["produto_id"], i["quantidade"]) for i in dados["itens"]] == [
        (cabo, 10),
        (conector, 4)
    ]
    assert all(i["movimentacao_id"] for i in dados["itens"])

    assert estoque(cliente, cabo) == 10
    assert estoque(cliente, conector) == 4

    movimentacoes = cliente.get(
        f"/movimentacoes?produto_id={cabo}"
    ).json()

    assert movimentacoes[0]["tipo"] == "ENTRADA"
    assert movimentacoes[0]["quantidade"] == 10
    assert movimentacoes[0]["recebimento_id"] == dados["id"]

    solicitacao = cliente.get(f"/solicitacoes-compra/{solicitacao_id}").json()

    assert solicitacao["status"] == "RECEBIDA"

    compra = cliente.get(f"/solicitacoes-compra/{solicitacao_id}/compra").json()

    assert compra["situacao_recebimento"] == "COMPLETO"
    assert compra["ultimo_recebimento"] == "2026-10-05"
    assert compra["entregue_no_prazo"] is True
    assert all(i["quantidade_pendente"] == 0 for i in compra["itens"])


def test_recebimento_parcial(cliente_autenticado):
    cliente = cliente_autenticado
    solicitacao_id, compra = compra_registrada(cliente)
    cabo, conector = (item["produto_id"] for item in compra["itens"])

    primeiro = receber(
        cliente,
        solicitacao_id,
        data_recebimento="2026-10-03",
        itens=[{"produto_id": cabo, "quantidade": 6}]
    )

    assert primeiro.status_code == 201
    assert estoque(cliente, cabo) == 6
    assert estoque(cliente, conector) == 0

    compra = cliente.get(f"/solicitacoes-compra/{solicitacao_id}/compra").json()
    pendentes = {i["produto_id"]: i["quantidade_pendente"] for i in compra["itens"]}

    assert compra["situacao_recebimento"] == "PARCIAL"
    assert compra["entregue_no_prazo"] is None
    assert pendentes == {cabo: 4, conector: 4}

    status = cliente.get(f"/solicitacoes-compra/{solicitacao_id}").json()["status"]
    assert status == "COMPRADA"

    segundo = receber(cliente, solicitacao_id, data_recebimento="2026-10-20")

    assert segundo.status_code == 201
    assert [(i["produto_id"], i["quantidade"]) for i in segundo.json()["itens"]] == [
        (cabo, 4),
        (conector, 4)
    ]

    compra = cliente.get(f"/solicitacoes-compra/{solicitacao_id}/compra").json()

    assert compra["situacao_recebimento"] == "COMPLETO"
    assert compra["entregue_no_prazo"] is False

    recebimentos = cliente.get(
        f"/solicitacoes-compra/{solicitacao_id}/compra/recebimentos"
    ).json()

    assert [r["id"] for r in recebimentos] == [
        primeiro.json()["id"],
        segundo.json()["id"]
    ]


def test_nao_receber_mais_que_o_pendente(cliente_autenticado):
    cliente = cliente_autenticado
    solicitacao_id, compra = compra_registrada(cliente)
    cabo = compra["itens"][0]["produto_id"]

    resposta = receber(
        cliente,
        solicitacao_id,
        itens=[{"produto_id": cabo, "quantidade": 11}]
    )

    assert resposta.status_code == 400
    assert resposta.json() == {
        "detail": "A quantidade recebida é maior que a quantidade pendente."
    }
    assert estoque(cliente, cabo) == 0


def test_nao_receber_produto_fora_da_compra(cliente_autenticado):
    cliente = cliente_autenticado
    solicitacao_id, _ = compra_registrada(cliente)

    resposta = receber(
        cliente,
        solicitacao_id,
        itens=[{"produto_id": 9999, "quantidade": 1}]
    )

    assert resposta.status_code == 400


def test_nao_receber_compra_ja_recebida(cliente_autenticado):
    cliente = cliente_autenticado
    solicitacao_id, _ = compra_registrada(cliente)

    receber(cliente, solicitacao_id, data_recebimento="2026-10-05")
    resposta = receber(cliente, solicitacao_id, data_recebimento="2026-10-05")

    assert resposta.status_code == 409
    assert resposta.json() == {
        "detail": "Todos os itens desta compra já foram recebidos."
    }


def test_nao_receber_sem_compra(cliente_autenticado):
    solicitacao_id, _ = solicitacao_aprovada(cliente_autenticado)

    resposta = receber(cliente_autenticado, solicitacao_id)

    assert resposta.status_code == 409
    assert resposta.json() == {
        "detail": "Registre a compra antes de receber os materiais."
    }


def test_data_de_recebimento_anterior_a_compra(cliente_autenticado):
    solicitacao_id, _ = compra_registrada(cliente_autenticado)

    resposta = receber(
        cliente_autenticado,
        solicitacao_id,
        data_recebimento="2026-09-01"
    )

    assert resposta.status_code == 400


def test_recebimento_com_dados_invalidos(cliente_autenticado):
    solicitacao_id, compra = compra_registrada(cliente_autenticado)
    cabo = compra["itens"][0]["produto_id"]

    casos = [
        {"itens": []},
        {"itens": [{"produto_id": cabo, "quantidade": 0}]},
        {
            "itens": [
                {"produto_id": cabo, "quantidade": 1},
                {"produto_id": cabo, "quantidade": 1}
            ]
        },
    ]

    for caso in casos:
        assert receber(cliente_autenticado, solicitacao_id, **caso).status_code == 422


def test_recebimento_de_solicitacao_inexistente(cliente_autenticado):
    assert receber(cliente_autenticado, 9999).status_code == 404

    resposta = cliente_autenticado.get(
        "/solicitacoes-compra/9999/compra/recebimentos"
    )

    assert resposta.status_code == 404


def test_filtrar_compras_por_situacao_e_periodo(cliente_autenticado):
    cliente = cliente_autenticado
    solicitacao_id, compra = compra_registrada(cliente, data_compra="2026-09-15")

    pendentes = cliente.get("/compras?situacao_recebimento=PENDENTE").json()
    completas = cliente.get("/compras?situacao_recebimento=COMPLETO").json()

    assert [c["id"] for c in pendentes] == [compra["id"]]
    assert completas == []

    receber(cliente, solicitacao_id, data_recebimento="2026-09-20")

    completas = cliente.get("/compras?situacao_recebimento=COMPLETO").json()
    em_setembro = cliente.get(
        "/compras?data_inicio=2026-09-01&data_fim=2026-09-30"
    ).json()
    em_outubro = cliente.get(
        "/compras?data_inicio=2026-10-01&data_fim=2026-10-31"
    ).json()

    assert [c["id"] for c in completas] == [compra["id"]]
    assert [c["id"] for c in em_setembro] == [compra["id"]]
    assert em_outubro == []

    invertido = cliente.get("/compras?data_inicio=2026-10-01&data_fim=2026-09-01")

    assert invertido.status_code == 400


def test_entrada_no_estoque_fica_na_data_do_recebimento(cliente_autenticado):
    from datetime import date

    cliente = cliente_autenticado
    solicitacao_id, _ = compra_registrada(cliente, data_compra="2026-01-10")

    assert receber(cliente, solicitacao_id, data_recebimento="2026-01-15").status_code == 201

    movimentacoes = cliente.get("/movimentacoes").json()
    assert movimentacoes
    assert all(m["data_movimentacao"].startswith("2026-01-15") for m in movimentacoes)

    _, compra_hoje = compra_registrada_hoje(cliente)
    assert compra_hoje is not None
    hoje = [m for m in cliente.get("/movimentacoes").json() if m["recebimento_id"] and not m["data_movimentacao"].startswith("2026-01-15")]
    assert all(m["data_movimentacao"].startswith(date.today().isoformat()) for m in hoje)


def compra_registrada_hoje(cliente):
    from datetime import date

    from backend.tests.apoio_compras import criar_fornecedor, registrar_cotacao, novo_cliente

    produto = cliente.post("/categorias", json={"nome": "Categoria Hoje"}).json()["id"]
    produto_id = cliente.post("/produtos", json={"nome": "Produto Hoje", "categoria_id": produto, "quantidade": 0, "preco": 1}).json()["id"]
    solicitacao_id = cliente.post("/solicitacoes-compra", json={"itens": [{"produto_id": produto_id, "quantidade": 2}]}).json()["id"]
    cotacao = registrar_cotacao(cliente, solicitacao_id, criar_fornecedor(cliente, "Fornecedor Hoje"), {produto_id: 1})
    novo_cliente("APROVADOR").patch(f"/solicitacoes-compra/{solicitacao_id}/aprovar", json={"cotacao_id": cotacao["id"]})
    compra = cliente.post(f"/solicitacoes-compra/{solicitacao_id}/compra", json={"data_compra": date.today().isoformat()}).json()
    assert receber(cliente, solicitacao_id).status_code == 201
    return solicitacao_id, compra
