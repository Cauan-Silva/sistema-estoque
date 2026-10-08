from backend.tests.apoio_compras import novo_cliente
from fastapi.testclient import TestClient

from backend.autenticacao import criar_token_acesso
from backend.main import app
from backend.repositorio_usuario import cadastrar_usuario


def criar_produto(cliente, nome="Cabo de rede"):
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
            "quantidade": 2,
            "preco": 10
        }
    )

    assert produto.status_code == 201

    return produto.json()["id"]


def criar_solicitacao(cliente, itens, observacao="Reposição mensal"):
    resposta = cliente.post(
        "/solicitacoes-compra",
        json={
            "observacao": observacao,
            "itens": itens
        }
    )

    assert resposta.status_code == 201

    return resposta.json()


def test_criar_solicitacao(cliente_autenticado):
    produto_id = criar_produto(cliente_autenticado)

    dados = criar_solicitacao(
        cliente_autenticado,
        [{"produto_id": produto_id, "quantidade": 20}]
    )

    assert dados["status"] == "ABERTA"
    assert dados["observacao"] == "Reposição mensal"
    assert dados["solicitante"] == "Usuario Testes"
    assert dados["itens"] == [
        {
            "id": dados["itens"][0]["id"],
            "produto_id": produto_id,
            "produto": "Cabo de rede",
            "quantidade": 20
        }
    ]


def test_criar_solicitacao_sem_itens(cliente_autenticado):
    resposta = cliente_autenticado.post(
        "/solicitacoes-compra",
        json={
            "itens": []
        }
    )

    assert resposta.status_code == 422


def test_criar_solicitacao_com_produto_repetido(cliente_autenticado):
    produto_id = criar_produto(cliente_autenticado)

    resposta = cliente_autenticado.post(
        "/solicitacoes-compra",
        json={
            "itens": [
                {"produto_id": produto_id, "quantidade": 1},
                {"produto_id": produto_id, "quantidade": 2}
            ]
        }
    )

    assert resposta.status_code == 422


def test_criar_solicitacao_com_quantidade_invalida(cliente_autenticado):
    produto_id = criar_produto(cliente_autenticado)

    resposta = cliente_autenticado.post(
        "/solicitacoes-compra",
        json={
            "itens": [
                {"produto_id": produto_id, "quantidade": 0}
            ]
        }
    )

    assert resposta.status_code == 422


def test_criar_solicitacao_com_produto_inexistente(cliente_autenticado):
    resposta = cliente_autenticado.post(
        "/solicitacoes-compra",
        json={
            "itens": [
                {"produto_id": 9999, "quantidade": 1}
            ]
        }
    )

    assert resposta.status_code == 404

    assert resposta.json() == {
        "detail": "Produto não encontrado."
    }


def test_buscar_solicitacao(cliente_autenticado):
    produto_id = criar_produto(cliente_autenticado)

    criada = criar_solicitacao(
        cliente_autenticado,
        [{"produto_id": produto_id, "quantidade": 5}]
    )

    resposta = cliente_autenticado.get(
        f"/solicitacoes-compra/{criada['id']}"
    )

    assert resposta.status_code == 200
    assert resposta.json() == criada


def test_buscar_solicitacao_inexistente(cliente_autenticado):
    resposta = cliente_autenticado.get(
        "/solicitacoes-compra/9999"
    )

    assert resposta.status_code == 404

    assert resposta.json() == {
        "detail": "Solicitação de compra não encontrada."
    }


def test_atualizar_solicitacao(cliente_autenticado):
    produto_a = criar_produto(cliente_autenticado, "Produto A")
    produto_b = criar_produto(cliente_autenticado, "Produto B")

    criada = criar_solicitacao(
        cliente_autenticado,
        [{"produto_id": produto_a, "quantidade": 5}]
    )

    resposta = cliente_autenticado.put(
        f"/solicitacoes-compra/{criada['id']}",
        json={
            "observacao": "Urgente",
            "itens": [
                {"produto_id": produto_a, "quantidade": 8},
                {"produto_id": produto_b, "quantidade": 3}
            ]
        }
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["observacao"] == "Urgente"
    assert [
        (item["produto_id"], item["quantidade"])
        for item in dados["itens"]
    ] == [
        (produto_a, 8),
        (produto_b, 3)
    ]


def test_atualizar_solicitacao_inexistente(cliente_autenticado):
    produto_id = criar_produto(cliente_autenticado)

    resposta = cliente_autenticado.put(
        "/solicitacoes-compra/9999",
        json={
            "itens": [
                {"produto_id": produto_id, "quantidade": 1}
            ]
        }
    )

    assert resposta.status_code == 404


def test_cancelar_solicitacao(cliente_autenticado):
    produto_id = criar_produto(cliente_autenticado)

    criada = criar_solicitacao(
        cliente_autenticado,
        [{"produto_id": produto_id, "quantidade": 5}]
    )

    resposta = cliente_autenticado.patch(
        f"/solicitacoes-compra/{criada['id']}/cancelar"
    )

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "CANCELADA"


def test_solicitacao_cancelada_nao_pode_ser_alterada(cliente_autenticado):
    produto_id = criar_produto(cliente_autenticado)

    criada = criar_solicitacao(
        cliente_autenticado,
        [{"produto_id": produto_id, "quantidade": 5}]
    )

    cliente_autenticado.patch(
        f"/solicitacoes-compra/{criada['id']}/cancelar"
    )

    edicao = cliente_autenticado.put(
        f"/solicitacoes-compra/{criada['id']}",
        json={
            "itens": [
                {"produto_id": produto_id, "quantidade": 1}
            ]
        }
    )

    novo_cancelamento = cliente_autenticado.patch(
        f"/solicitacoes-compra/{criada['id']}/cancelar"
    )

    assert edicao.status_code == 409
    assert edicao.json() == {
        "detail": "Apenas solicitações abertas podem ser alteradas."
    }

    assert novo_cancelamento.status_code == 409
    assert novo_cancelamento.json() == {
        "detail": "Esta solicitação não pode mais ser cancelada."
    }


def test_listar_e_filtrar_solicitacoes(cliente_autenticado):
    produto_id = criar_produto(cliente_autenticado)
    item = [{"produto_id": produto_id, "quantidade": 1}]

    aberta = criar_solicitacao(cliente_autenticado, item)
    cancelada = criar_solicitacao(cliente_autenticado, item)

    cliente_autenticado.patch(
        f"/solicitacoes-compra/{cancelada['id']}/cancelar"
    )

    todas = cliente_autenticado.get("/solicitacoes-compra").json()
    abertas = cliente_autenticado.get(
        "/solicitacoes-compra?status=ABERTA"
    ).json()
    canceladas = cliente_autenticado.get(
        "/solicitacoes-compra?status=CANCELADA"
    ).json()

    assert [s["id"] for s in todas] == [cancelada["id"], aberta["id"]]
    assert [s["id"] for s in abertas] == [aberta["id"]]
    assert [s["id"] for s in canceladas] == [cancelada["id"]]


def test_filtrar_status_invalido(cliente_autenticado):
    resposta = cliente_autenticado.get(
        "/solicitacoes-compra?status=QUALQUER"
    )

    assert resposta.status_code == 422


def test_paginacao_solicitacoes(cliente_autenticado):
    produto_id = criar_produto(cliente_autenticado)
    item = [{"produto_id": produto_id, "quantidade": 1}]

    ids = [
        criar_solicitacao(cliente_autenticado, item)["id"]
        for _ in range(3)
    ]

    pagina_1 = cliente_autenticado.get(
        "/solicitacoes-compra?pagina=1&tamanho=2"
    ).json()
    pagina_2 = cliente_autenticado.get(
        "/solicitacoes-compra?pagina=2&tamanho=2"
    ).json()

    assert [s["id"] for s in pagina_1] == [ids[2], ids[1]]
    assert [s["id"] for s in pagina_2] == [ids[0]]


def test_filtrar_apenas_minhas_solicitacoes(cliente_autenticado):
    produto_id = criar_produto(cliente_autenticado)
    item = [{"produto_id": produto_id, "quantidade": 1}]

    minha = criar_solicitacao(cliente_autenticado, item)

    outro_cliente = novo_cliente("COMPRADOR", "Outro Usuario")
    de_outro = criar_solicitacao(outro_cliente, item)

    assert de_outro["solicitante"] == "Outro Usuario"

    minhas = cliente_autenticado.get(
        "/solicitacoes-compra?apenas_minhas=true"
    ).json()

    assert [s["id"] for s in minhas] == [minha["id"]]


def test_nao_excluir_produto_em_solicitacao(cliente_autenticado):
    produto_id = criar_produto(cliente_autenticado)

    criar_solicitacao(
        cliente_autenticado,
        [{"produto_id": produto_id, "quantidade": 1}]
    )

    resposta = cliente_autenticado.delete(
        f"/produtos/{produto_id}"
    )

    assert resposta.status_code == 409

    assert resposta.json() == {
        "detail": (
            "Não é possível excluir um produto "
            "vinculado a solicitações de compra."
        )
    }
