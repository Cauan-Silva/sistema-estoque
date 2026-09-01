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
    preco=199.90
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


def test_registrar_entrada(client):
    categoria_id = criar_categoria(client)

    produto_id = criar_produto(
        client,
        categoria_id,
        quantidade=10
    )

    resposta = client.post(
        "/movimentacoes",
        json={
            "produto_id": produto_id,
            "tipo": "ENTRADA",
            "quantidade": 5
        }
    )

    assert resposta.status_code == 201

    dados = resposta.json()

    assert dados["produto_id"] == produto_id
    assert dados["tipo"] == "ENTRADA"
    assert dados["quantidade"] == 5

    produto = client.get(
        f"/produtos/{produto_id}"
    )

    assert produto.status_code == 200
    assert produto.json()["quantidade"] == 15


def test_registrar_saida(client):
    categoria_id = criar_categoria(client)

    produto_id = criar_produto(
        client,
        categoria_id,
        quantidade=10
    )

    resposta = client.post(
        "/movimentacoes",
        json={
            "produto_id": produto_id,
            "tipo": "SAIDA",
            "quantidade": 4
        }
    )

    assert resposta.status_code == 201

    produto = client.get(
        f"/produtos/{produto_id}"
    )

    assert produto.status_code == 200
    assert produto.json()["quantidade"] == 6


def test_impedir_saida_com_estoque_insuficiente(
    client
):
    categoria_id = criar_categoria(client)

    produto_id = criar_produto(
        client,
        categoria_id,
        quantidade=5
    )

    resposta = client.post(
        "/movimentacoes",
        json={
            "produto_id": produto_id,
            "tipo": "SAIDA",
            "quantidade": 10
        }
    )

    assert resposta.status_code == 409

    assert resposta.json() == {
        "detail": (
            "Estoque insuficiente para "
            "realizar a saída."
        )
    }

    produto = client.get(
        f"/produtos/{produto_id}"
    )

    assert produto.json()["quantidade"] == 5


def test_movimentacao_produto_inexistente(
    client
):
    resposta = client.post(
        "/movimentacoes",
        json={
            "produto_id": 9999,
            "tipo": "ENTRADA",
            "quantidade": 5
        }
    )

    assert resposta.status_code == 404

    assert resposta.json() == {
        "detail": "Produto não encontrado."
    }


def test_listar_movimentacoes(client):
    categoria_id = criar_categoria(client)

    produto_id = criar_produto(
        client,
        categoria_id,
        quantidade=10
    )

    client.post(
        "/movimentacoes",
        json={
            "produto_id": produto_id,
            "tipo": "ENTRADA",
            "quantidade": 5
        }
    )

    client.post(
        "/movimentacoes",
        json={
            "produto_id": produto_id,
            "tipo": "SAIDA",
            "quantidade": 2
        }
    )

    resposta = client.get(
        "/movimentacoes"
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert len(dados) == 2


def test_buscar_movimentacao_por_id(client):
    categoria_id = criar_categoria(client)

    produto_id = criar_produto(
        client,
        categoria_id
    )

    criacao = client.post(
        "/movimentacoes",
        json={
            "produto_id": produto_id,
            "tipo": "ENTRADA",
            "quantidade": 5
        }
    )

    movimentacao_id = criacao.json()["id"]

    resposta = client.get(
        f"/movimentacoes/{movimentacao_id}"
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["id"] == movimentacao_id
    assert dados["produto_id"] == produto_id


def test_movimentacao_inexistente(client):
    resposta = client.get(
        "/movimentacoes/9999"
    )

    assert resposta.status_code == 404


def test_filtro_movimentacao_por_tipo(client):
    categoria_id = criar_categoria(client)

    produto_id = criar_produto(
        client,
        categoria_id,
        quantidade=20
    )

    client.post(
        "/movimentacoes",
        json={
            "produto_id": produto_id,
            "tipo": "ENTRADA",
            "quantidade": 5
        }
    )

    client.post(
        "/movimentacoes",
        json={
            "produto_id": produto_id,
            "tipo": "SAIDA",
            "quantidade": 3
        }
    )

    resposta = client.get(
        "/movimentacoes",
        params={
            "tipo": "SAIDA"
        }
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert len(dados) == 1
    assert dados[0]["tipo"] == "SAIDA"


def test_filtro_movimentacao_por_produto(client):
    categoria_id = criar_categoria(client)

    produto_1 = criar_produto(
        client,
        categoria_id,
        nome="Produto 1"
    )

    produto_2 = criar_produto(
        client,
        categoria_id,
        nome="Produto 2"
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
            "produto_id": produto_2,
            "tipo": "ENTRADA",
            "quantidade": 5
        }
    )

    resposta = client.get(
        "/movimentacoes",
        params={
            "produto_id": produto_1
        }
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert len(dados) == 1
    assert dados[0]["produto_id"] == produto_1


def test_validacao_tipo_movimentacao(client):
    categoria_id = criar_categoria(client)

    produto_id = criar_produto(
        client,
        categoria_id
    )

    resposta = client.post(
        "/movimentacoes",
        json={
            "produto_id": produto_id,
            "tipo": "TESTE",
            "quantidade": 5
        }
    )

    assert resposta.status_code == 422


def test_validacao_quantidade_movimentacao(
    client
):
    categoria_id = criar_categoria(client)

    produto_id = criar_produto(
        client,
        categoria_id
    )

    resposta = client.post(
        "/movimentacoes",
        json={
            "produto_id": produto_id,
            "tipo": "ENTRADA",
            "quantidade": 0
        }
    )

    assert resposta.status_code == 422