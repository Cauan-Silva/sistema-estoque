def criar_categoria(client, nome="Switches"):
    resposta = client.post(
        "/categorias",
        json={
            "nome": nome
        }
    )

    assert resposta.status_code == 201

    return resposta.json()["id"]


def criar_produto(
    client,
    categoria_id,
    nome="Switch Intelbras",
    quantidade=10,
    preco=100.0
):
    resposta = client.post(
        "/produtos",
        json={
            "nome": nome,
            "categoria_id": categoria_id,
            "quantidade": quantidade,
            "preco": preco
        }
    )

    assert resposta.status_code == 201

    return resposta.json()["id"]


def test_relatorio_resumo(client):
    categoria_id = criar_categoria(client)

    produto_1 = criar_produto(
        client,
        categoria_id,
        nome="Produto A",
        quantidade=10,
        preco=100
    )

    criar_produto(
        client,
        categoria_id,
        nome="Produto B",
        quantidade=3,
        preco=50
    )

    client.post(
        "/movimentacoes",
        json={
            "produto_id": produto_1,
            "tipo": "ENTRADA",
            "quantidade": 5
        }
    )

    client.post(
        "/movimentacoes",
        json={
            "produto_id": produto_1,
            "tipo": "SAIDA",
            "quantidade": 2
        }
    )

    resposta = client.get(
        "/relatorios/resumo",
        params={
            "limite_estoque": 5
        }
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["total_produtos"] == 2
    assert dados["total_categorias"] == 1
    assert dados["unidades_em_estoque"] == 16
    assert dados["produtos_estoque_baixo"] == 1
    assert dados["valor_total_estoque"] == 1450
    assert dados["total_entradas"] == 5
    assert dados["total_saidas"] == 2


def test_relatorio_maior_valor(client):
    categoria_id = criar_categoria(client)

    criar_produto(
        client,
        categoria_id,
        nome="Produto Barato",
        quantidade=2,
        preco=10
    )

    criar_produto(
        client,
        categoria_id,
        nome="Produto Caro",
        quantidade=10,
        preco=100
    )

    resposta = client.get(
        "/relatorios/maior-valor"
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert len(dados) == 2

    assert dados[0]["nome"] == "Produto Caro"
    assert dados[0]["valor_estoque"] == 1000

    assert dados[1]["nome"] == "Produto Barato"
    assert dados[1]["valor_estoque"] == 20


def test_relatorio_maior_valor_com_limite(client):
    categoria_id = criar_categoria(client)

    criar_produto(
        client,
        categoria_id,
        nome="Produto 1",
        quantidade=10,
        preco=100
    )

    criar_produto(
        client,
        categoria_id,
        nome="Produto 2",
        quantidade=5,
        preco=100
    )

    criar_produto(
        client,
        categoria_id,
        nome="Produto 3",
        quantidade=1,
        preco=100
    )

    resposta = client.get(
        "/relatorios/maior-valor",
        params={
            "limite": 2
        }
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert len(dados) == 2

    assert dados[0]["nome"] == "Produto 1"
    assert dados[1]["nome"] == "Produto 2"


def test_relatorio_resumo_banco_vazio(client):
    resposta = client.get(
        "/relatorios/resumo"
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados == {
        "total_produtos": 0,
        "total_categorias": 0,
        "unidades_em_estoque": 0,
        "produtos_estoque_baixo": 0,
        "valor_total_estoque": 0.0,
        "total_entradas": 0,
        "total_saidas": 0
    }


def test_validacao_limite_relatorio(client):
    resposta = client.get(
        "/relatorios/maior-valor",
        params={
            "limite": 0
        }
    )

    assert resposta.status_code == 422