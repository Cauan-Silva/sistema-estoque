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

    return resposta


def test_criar_produto(client):
    categoria_id = criar_categoria(client)

    resposta = criar_produto(
        client,
        categoria_id
    )

    dados = resposta.json()

    assert dados["id"] == 1
    assert dados["nome"] == "Switch Intelbras"
    assert dados["categoria_id"] == categoria_id
    assert dados["categoria"] == "Switches"
    assert dados["quantidade"] == 10
    assert dados["preco"] == 199.90


def test_listar_produtos(client):
    categoria_id = criar_categoria(client)

    criar_produto(
        client,
        categoria_id,
        nome="Switch 8 Portas"
    )

    criar_produto(
        client,
        categoria_id,
        nome="Switch 16 Portas"
    )

    resposta = client.get(
        "/produtos"
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert len(dados) == 2


def test_buscar_produto_por_id(client):
    categoria_id = criar_categoria(client)

    criacao = criar_produto(
        client,
        categoria_id
    )

    produto_id = criacao.json()["id"]

    resposta = client.get(
        f"/produtos/{produto_id}"
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["id"] == produto_id
    assert dados["nome"] == "Switch Intelbras"


def test_produto_inexistente(client):
    resposta = client.get(
        "/produtos/9999"
    )

    assert resposta.status_code == 404

    assert resposta.json() == {
        "detail": "Produto não encontrado."
    }


def test_categoria_inexistente_ao_criar_produto(client):
    resposta = client.post(
        "/produtos",
        json={
            "nome": "Produto Teste",
            "categoria_id": 9999,
            "quantidade": 10,
            "preco": 100
        }
    )

    assert resposta.status_code == 404

    assert resposta.json() == {
        "detail": "Categoria não encontrada."
    }


def test_atualizar_produto(client):
    categoria_id = criar_categoria(client)

    criacao = criar_produto(
        client,
        categoria_id
    )

    produto_id = criacao.json()["id"]

    resposta = client.put(
        f"/produtos/{produto_id}",
        json={
            "nome": "Switch Atualizado",
            "categoria_id": categoria_id,
            "quantidade": 20,
            "preco": 299.90
        }
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["nome"] == "Switch Atualizado"
    assert dados["quantidade"] == 20
    assert dados["preco"] == 299.90


def test_excluir_produto(client):
    categoria_id = criar_categoria(client)

    criacao = criar_produto(
        client,
        categoria_id
    )

    produto_id = criacao.json()["id"]

    resposta = client.delete(
        f"/produtos/{produto_id}"
    )

    assert resposta.status_code == 204

    consulta = client.get(
        f"/produtos/{produto_id}"
    )

    assert consulta.status_code == 404


def test_busca_produto_por_nome(client):
    categoria_id = criar_categoria(client)

    criar_produto(
        client,
        categoria_id,
        nome="Switch Intelbras"
    )

    criar_produto(
        client,
        categoria_id,
        nome="Roteador TP-Link"
    )

    resposta = client.get(
        "/produtos",
        params={
            "busca": "Intelbras"
        }
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert len(dados) == 1
    assert dados[0]["nome"] == "Switch Intelbras"


def test_filtro_produto_por_categoria(client):
    categoria_switch = criar_categoria(
        client,
        "Switches"
    )

    categoria_roteador = criar_categoria(
        client,
        "Roteadores"
    )

    criar_produto(
        client,
        categoria_switch,
        nome="Switch Intelbras"
    )

    criar_produto(
        client,
        categoria_roteador,
        nome="Roteador Intelbras"
    )

    resposta = client.get(
        "/produtos",
        params={
            "categoria_id": categoria_switch
        }
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert len(dados) == 1
    assert dados[0]["categoria"] == "Switches"


def test_filtro_estoque_baixo(client):
    categoria_id = criar_categoria(client)

    criar_produto(
        client,
        categoria_id,
        nome="Produto Estoque Baixo",
        quantidade=3
    )

    criar_produto(
        client,
        categoria_id,
        nome="Produto Estoque Alto",
        quantidade=20
    )

    resposta = client.get(
        "/produtos",
        params={
            "estoque_baixo": True,
            "limite_estoque": 5
        }
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert len(dados) == 1
    assert (
        dados[0]["nome"]
        == "Produto Estoque Baixo"
    )


def test_validacao_produto(client):
    categoria_id = criar_categoria(client)

    resposta = client.post(
        "/produtos",
        json={
            "nome": "A",
            "categoria_id": categoria_id,
            "quantidade": -1,
            "preco": -10
        }
    )

    assert resposta.status_code == 422