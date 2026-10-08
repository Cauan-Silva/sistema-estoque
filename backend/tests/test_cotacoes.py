def criar_produto(cliente, nome):
    categoria = cliente.post(
        "/categorias",
        json={
            "nome": f"Categoria {nome}"
        }
    )

    assert categoria.status_code == 201

    produto = cliente.post(
        "/produtos",
        json={
            "nome": nome,
            "categoria_id": categoria.json()["id"],
            "quantidade": 0,
            "preco": 10
        }
    )

    assert produto.status_code == 201

    return produto.json()["id"]


def criar_fornecedor(cliente, nome="Fornecedor Cotação"):
    resposta = cliente.post(
        "/fornecedores",
        json={
            "nome": nome
        }
    )

    assert resposta.status_code == 201

    return resposta.json()["id"]


def preparar(cliente):
    produto_a = criar_produto(cliente, "Cabo")
    produto_b = criar_produto(cliente, "Conector")

    solicitacao = cliente.post(
        "/solicitacoes-compra",
        json={
            "itens": [
                {"produto_id": produto_a, "quantidade": 10},
                {"produto_id": produto_b, "quantidade": 3}
            ]
        }
    )

    assert solicitacao.status_code == 201

    return solicitacao.json()["id"], produto_a, produto_b


def registrar_cotacao(
    cliente,
    solicitacao_id,
    fornecedor_id,
    itens,
    frete=15.5,
    prazo=7
):
    return cliente.post(
        f"/solicitacoes-compra/{solicitacao_id}/cotacoes",
        json={
            "fornecedor_id": fornecedor_id,
            "frete": frete,
            "prazo_entrega_dias": prazo,
            "validade": "2026-12-31",
            "observacao": "Pagamento em 30 dias",
            "itens": itens
        }
    )


def status_solicitacao(cliente, solicitacao_id):
    return cliente.get(
        f"/solicitacoes-compra/{solicitacao_id}"
    ).json()["status"]


def test_registrar_cotacao(cliente_autenticado):
    solicitacao_id, produto_a, produto_b = preparar(cliente_autenticado)
    fornecedor_id = criar_fornecedor(cliente_autenticado)

    resposta = registrar_cotacao(
        cliente_autenticado,
        solicitacao_id,
        fornecedor_id,
        [
            {"produto_id": produto_a, "preco_unitario": 2.35},
            {"produto_id": produto_b, "preco_unitario": 1.10}
        ]
    )

    assert resposta.status_code == 201

    dados = resposta.json()

    assert dados["solicitacao_id"] == solicitacao_id
    assert dados["fornecedor"] == "Fornecedor Cotação"
    assert dados["prazo_entrega_dias"] == 7
    assert dados["validade"] == "2026-12-31"
    assert dados["itens"] == [
        {
            "produto_id": produto_a,
            "produto": "Cabo",
            "quantidade": 10,
            "preco_unitario": 2.35,
            "subtotal": 23.5
        },
        {
            "produto_id": produto_b,
            "produto": "Conector",
            "quantidade": 3,
            "preco_unitario": 1.1,
            "subtotal": 3.3
        }
    ]
    assert dados["valor_itens"] == 26.8
    assert dados["frete"] == 15.5
    assert dados["valor_total"] == 42.3


def test_primeira_cotacao_muda_status_para_em_cotacao(cliente_autenticado):
    solicitacao_id, produto_a, _ = preparar(cliente_autenticado)
    fornecedor_id = criar_fornecedor(cliente_autenticado)

    assert status_solicitacao(cliente_autenticado, solicitacao_id) == "ABERTA"

    registrar_cotacao(
        cliente_autenticado,
        solicitacao_id,
        fornecedor_id,
        [{"produto_id": produto_a, "preco_unitario": 2}]
    )

    assert (
        status_solicitacao(cliente_autenticado, solicitacao_id)
        == "EM_COTACAO"
    )


def test_solicitacao_em_cotacao_nao_permite_editar_itens(cliente_autenticado):
    solicitacao_id, produto_a, _ = preparar(cliente_autenticado)
    fornecedor_id = criar_fornecedor(cliente_autenticado)

    registrar_cotacao(
        cliente_autenticado,
        solicitacao_id,
        fornecedor_id,
        [{"produto_id": produto_a, "preco_unitario": 2}]
    )

    resposta = cliente_autenticado.put(
        f"/solicitacoes-compra/{solicitacao_id}",
        json={
            "itens": [
                {"produto_id": produto_a, "quantidade": 1}
            ]
        }
    )

    assert resposta.status_code == 409


def test_solicitacao_em_cotacao_pode_ser_cancelada(cliente_autenticado):
    solicitacao_id, produto_a, _ = preparar(cliente_autenticado)
    fornecedor_id = criar_fornecedor(cliente_autenticado)

    registrar_cotacao(
        cliente_autenticado,
        solicitacao_id,
        fornecedor_id,
        [{"produto_id": produto_a, "preco_unitario": 2}]
    )

    resposta = cliente_autenticado.patch(
        f"/solicitacoes-compra/{solicitacao_id}/cancelar"
    )

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "CANCELADA"

    nova_cotacao = registrar_cotacao(
        cliente_autenticado,
        solicitacao_id,
        criar_fornecedor(cliente_autenticado, "Outro Fornecedor"),
        [{"produto_id": produto_a, "preco_unitario": 2}]
    )

    assert nova_cotacao.status_code == 409


def test_cotacao_em_solicitacao_inexistente(cliente_autenticado):
    fornecedor_id = criar_fornecedor(cliente_autenticado)

    resposta = registrar_cotacao(
        cliente_autenticado,
        9999,
        fornecedor_id,
        [{"produto_id": 1, "preco_unitario": 2}]
    )

    assert resposta.status_code == 404

    assert resposta.json() == {
        "detail": "Solicitação de compra não encontrada."
    }


def test_cotacao_com_fornecedor_inexistente(cliente_autenticado):
    solicitacao_id, produto_a, _ = preparar(cliente_autenticado)

    resposta = registrar_cotacao(
        cliente_autenticado,
        solicitacao_id,
        9999,
        [{"produto_id": produto_a, "preco_unitario": 2}]
    )

    assert resposta.status_code == 404

    assert resposta.json() == {
        "detail": "Fornecedor não encontrado."
    }


def test_cotacao_com_fornecedor_inativo(cliente_autenticado):
    solicitacao_id, produto_a, _ = preparar(cliente_autenticado)
    fornecedor_id = criar_fornecedor(cliente_autenticado)

    cliente_autenticado.patch(
        f"/fornecedores/{fornecedor_id}/status",
        json={
            "ativo": False
        }
    )

    resposta = registrar_cotacao(
        cliente_autenticado,
        solicitacao_id,
        fornecedor_id,
        [{"produto_id": produto_a, "preco_unitario": 2}]
    )

    assert resposta.status_code == 400

    assert resposta.json() == {
        "detail": "Fornecedor inativo."
    }


def test_cotacao_com_produto_fora_da_solicitacao(cliente_autenticado):
    solicitacao_id, _, _ = preparar(cliente_autenticado)
    fornecedor_id = criar_fornecedor(cliente_autenticado)
    produto_extra = criar_produto(cliente_autenticado, "Extra")

    resposta = registrar_cotacao(
        cliente_autenticado,
        solicitacao_id,
        fornecedor_id,
        [{"produto_id": produto_extra, "preco_unitario": 2}]
    )

    assert resposta.status_code == 400

    assert resposta.json() == {
        "detail": "A cotação só pode conter produtos da solicitação."
    }


def test_cotacao_duplicada_para_mesmo_fornecedor(cliente_autenticado):
    solicitacao_id, produto_a, _ = preparar(cliente_autenticado)
    fornecedor_id = criar_fornecedor(cliente_autenticado)
    itens = [{"produto_id": produto_a, "preco_unitario": 2}]

    primeira = registrar_cotacao(
        cliente_autenticado,
        solicitacao_id,
        fornecedor_id,
        itens
    )
    segunda = registrar_cotacao(
        cliente_autenticado,
        solicitacao_id,
        fornecedor_id,
        itens
    )

    assert primeira.status_code == 201
    assert segunda.status_code == 409


def test_cotacao_com_dados_invalidos(cliente_autenticado):
    solicitacao_id, produto_a, _ = preparar(cliente_autenticado)
    fornecedor_id = criar_fornecedor(cliente_autenticado)

    casos = [
        {"itens": []},
        {"itens": [{"produto_id": produto_a, "preco_unitario": -1}]},
        {
            "itens": [
                {"produto_id": produto_a, "preco_unitario": 1},
                {"produto_id": produto_a, "preco_unitario": 2}
            ]
        },
    ]

    for caso in casos:
        resposta = cliente_autenticado.post(
            f"/solicitacoes-compra/{solicitacao_id}/cotacoes",
            json={
                "fornecedor_id": fornecedor_id,
                "prazo_entrega_dias": 5,
                **caso
            }
        )

        assert resposta.status_code == 422

    frete_negativo = registrar_cotacao(
        cliente_autenticado,
        solicitacao_id,
        fornecedor_id,
        [{"produto_id": produto_a, "preco_unitario": 1}],
        frete=-5
    )

    assert frete_negativo.status_code == 422


def test_listar_e_buscar_cotacoes(cliente_autenticado):
    solicitacao_id, produto_a, _ = preparar(cliente_autenticado)
    fornecedor_a = criar_fornecedor(cliente_autenticado, "Fornecedor A")
    fornecedor_b = criar_fornecedor(cliente_autenticado, "Fornecedor B")
    itens = [{"produto_id": produto_a, "preco_unitario": 2}]

    cotacao_a = registrar_cotacao(
        cliente_autenticado,
        solicitacao_id,
        fornecedor_a,
        itens
    ).json()
    cotacao_b = registrar_cotacao(
        cliente_autenticado,
        solicitacao_id,
        fornecedor_b,
        itens
    ).json()

    lista = cliente_autenticado.get(
        f"/solicitacoes-compra/{solicitacao_id}/cotacoes"
    )

    assert lista.status_code == 200
    assert [c["id"] for c in lista.json()] == [
        cotacao_a["id"],
        cotacao_b["id"]
    ]

    detalhe = cliente_autenticado.get(
        f"/solicitacoes-compra/{solicitacao_id}/cotacoes/{cotacao_b['id']}"
    )

    assert detalhe.status_code == 200
    assert detalhe.json() == cotacao_b


def test_listar_cotacoes_de_solicitacao_inexistente(cliente_autenticado):
    resposta = cliente_autenticado.get(
        "/solicitacoes-compra/9999/cotacoes"
    )

    assert resposta.status_code == 404


def test_buscar_cotacao_de_outra_solicitacao(cliente_autenticado):
    solicitacao_id, produto_a, _ = preparar(cliente_autenticado)
    fornecedor_id = criar_fornecedor(cliente_autenticado)

    cotacao = registrar_cotacao(
        cliente_autenticado,
        solicitacao_id,
        fornecedor_id,
        [{"produto_id": produto_a, "preco_unitario": 2}]
    ).json()

    resposta = cliente_autenticado.get(
        f"/solicitacoes-compra/{solicitacao_id + 1}/cotacoes/{cotacao['id']}"
    )

    assert resposta.status_code == 404

    assert resposta.json() == {
        "detail": "Cotação não encontrada."
    }


def test_atualizar_cotacao(cliente_autenticado):
    solicitacao_id, produto_a, produto_b = preparar(cliente_autenticado)
    fornecedor_id = criar_fornecedor(cliente_autenticado)

    cotacao = registrar_cotacao(
        cliente_autenticado,
        solicitacao_id,
        fornecedor_id,
        [{"produto_id": produto_a, "preco_unitario": 2}]
    ).json()

    resposta = cliente_autenticado.put(
        f"/solicitacoes-compra/{solicitacao_id}/cotacoes/{cotacao['id']}",
        json={
            "frete": 0,
            "prazo_entrega_dias": 3,
            "itens": [
                {"produto_id": produto_a, "preco_unitario": 1.5},
                {"produto_id": produto_b, "preco_unitario": 4}
            ]
        }
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["prazo_entrega_dias"] == 3
    assert dados["validade"] is None
    assert dados["valor_itens"] == 27.0
    assert dados["valor_total"] == 27.0
    assert len(dados["itens"]) == 2


def test_atualizar_cotacao_inexistente(cliente_autenticado):
    solicitacao_id, produto_a, _ = preparar(cliente_autenticado)

    resposta = cliente_autenticado.put(
        f"/solicitacoes-compra/{solicitacao_id}/cotacoes/9999",
        json={
            "prazo_entrega_dias": 3,
            "itens": [
                {"produto_id": produto_a, "preco_unitario": 1}
            ]
        }
    )

    assert resposta.status_code == 404


def test_excluir_ultima_cotacao_reabre_solicitacao(cliente_autenticado):
    solicitacao_id, produto_a, _ = preparar(cliente_autenticado)
    fornecedor_a = criar_fornecedor(cliente_autenticado, "Fornecedor A")
    fornecedor_b = criar_fornecedor(cliente_autenticado, "Fornecedor B")
    itens = [{"produto_id": produto_a, "preco_unitario": 2}]

    cotacao_a = registrar_cotacao(
        cliente_autenticado,
        solicitacao_id,
        fornecedor_a,
        itens
    ).json()
    cotacao_b = registrar_cotacao(
        cliente_autenticado,
        solicitacao_id,
        fornecedor_b,
        itens
    ).json()

    url = f"/solicitacoes-compra/{solicitacao_id}/cotacoes"

    assert cliente_autenticado.delete(
        f"{url}/{cotacao_a['id']}"
    ).status_code == 204

    assert (
        status_solicitacao(cliente_autenticado, solicitacao_id)
        == "EM_COTACAO"
    )

    assert cliente_autenticado.delete(
        f"{url}/{cotacao_b['id']}"
    ).status_code == 204

    assert (
        status_solicitacao(cliente_autenticado, solicitacao_id)
        == "ABERTA"
    )

    assert cliente_autenticado.get(url).json() == []


def test_excluir_cotacao_inexistente(cliente_autenticado):
    solicitacao_id, _, _ = preparar(cliente_autenticado)

    resposta = cliente_autenticado.delete(
        f"/solicitacoes-compra/{solicitacao_id}/cotacoes/9999"
    )

    assert resposta.status_code == 404
