def test_criar_categoria(cliente_autenticado):
    resposta = cliente_autenticado.post(
        "/categorias",
        json={
            "nome": "Switches"
        }
    )

    assert resposta.status_code == 201

    dados = resposta.json()

    assert dados["id"] == 1
    assert dados["nome"] == "Switches"


def test_listar_categorias(cliente_autenticado):
    cliente_autenticado.post(
        "/categorias",
        json={
            "nome": "Switches"
        }
    )

    cliente_autenticado.post(
        "/categorias",
        json={
            "nome": "Roteadores"
        }
    )

    resposta = cliente_autenticado.get(
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


def test_buscar_categoria_por_id(cliente_autenticado):
    criacao = cliente_autenticado.post(
        "/categorias",
        json={
            "nome": "ONU"
        }
    )

    categoria_id = criacao.json()["id"]

    resposta = cliente_autenticado.get(
        f"/categorias/{categoria_id}"
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["id"] == categoria_id
    assert dados["nome"] == "ONU"


def test_buscar_categoria_inexistente(cliente_autenticado):
    resposta = cliente_autenticado.get(
        "/categorias/9999"
    )

    assert resposta.status_code == 404

    assert resposta.json() == {
        "detail": "Categoria não encontrada."
    }


def test_atualizar_categoria(cliente_autenticado):
    criacao = cliente_autenticado.post(
        "/categorias",
        json={
            "nome": "Switch"
        }
    )

    categoria_id = criacao.json()["id"]

    resposta = cliente_autenticado.put(
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


def test_excluir_categoria(cliente_autenticado):
    criacao = cliente_autenticado.post(
        "/categorias",
        json={
            "nome": "Temporaria"
        }
    )

    categoria_id = criacao.json()["id"]

    resposta = cliente_autenticado.delete(
        f"/categorias/{categoria_id}"
    )

    assert resposta.status_code == 204

    consulta = cliente_autenticado.get(
        f"/categorias/{categoria_id}"
    )

    assert consulta.status_code == 404


def test_categoria_duplicada(cliente_autenticado):
    cliente_autenticado.post(
        "/categorias",
        json={
            "nome": "Switches"
        }
    )

    resposta = cliente_autenticado.post(
        "/categorias",
        json={
            "nome": "Switches"
        }
    )

    assert resposta.status_code == 409

    assert resposta.json() == {
        "detail": "Categoria já cadastrada."
    }


def test_validacao_nome_categoria(cliente_autenticado):
    resposta = cliente_autenticado.post(
        "/categorias",
        json={
            "nome": "A"
        }
    )

    assert resposta.status_code == 422