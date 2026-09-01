def test_criar_categoria(client):
    resposta = client.post(
        "/categorias",
        json={
            "nome": "Switches"
        }
    )

    assert resposta.status_code == 201

    dados = resposta.json()

    assert dados["id"] == 1
    assert dados["nome"] == "Switches"


def test_listar_categorias(client):
    client.post(
        "/categorias",
        json={
            "nome": "Switches"
        }
    )

    client.post(
        "/categorias",
        json={
            "nome": "Roteadores"
        }
    )

    resposta = client.get(
        "/categorias"
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert len(dados) == 2

    nomes = [
        categoria["nome"]
        for categoria in dados
    ]

    assert "Switches" in nomes
    assert "Roteadores" in nomes


def test_buscar_categoria_por_id(client):
    criacao = client.post(
        "/categorias",
        json={
            "nome": "ONU"
        }
    )

    categoria_id = criacao.json()["id"]

    resposta = client.get(
        f"/categorias/{categoria_id}"
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["id"] == categoria_id
    assert dados["nome"] == "ONU"


def test_buscar_categoria_inexistente(client):
    resposta = client.get(
        "/categorias/9999"
    )

    assert resposta.status_code == 404

    assert resposta.json() == {
        "detail": "Categoria não encontrada."
    }


def test_atualizar_categoria(client):
    criacao = client.post(
        "/categorias",
        json={
            "nome": "Switch"
        }
    )

    categoria_id = criacao.json()["id"]

    resposta = client.put(
        f"/categorias/{categoria_id}",
        json={
            "nome": "Switches de Rede"
        }
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["id"] == categoria_id
    assert (
        dados["nome"]
        == "Switches de Rede"
    )


def test_excluir_categoria(client):
    criacao = client.post(
        "/categorias",
        json={
            "nome": "Temporaria"
        }
    )

    categoria_id = criacao.json()["id"]

    resposta = client.delete(
        f"/categorias/{categoria_id}"
    )

    assert resposta.status_code == 204

    consulta = client.get(
        f"/categorias/{categoria_id}"
    )

    assert consulta.status_code == 404


def test_categoria_duplicada(client):
    client.post(
        "/categorias",
        json={
            "nome": "Switches"
        }
    )

    resposta = client.post(
        "/categorias",
        json={
            "nome": "Switches"
        }
    )

    assert resposta.status_code == 409

    assert resposta.json() == {
        "detail": "Categoria já cadastrada."
    }


def test_validacao_nome_categoria(client):
    resposta = client.post(
        "/categorias",
        json={
            "nome": "A"
        }
    )

    assert resposta.status_code == 422