def criar_categoria(cliente_autenticado, nome="Switches"):
    resposta = cliente_autenticado.post(
        "/categorias",
        json={
            "nome": nome
        }
    )

    assert resposta.status_code == 201

    return resposta.json()["id"]


def criar_produto(
    cliente_autenticado,
    categoria_id,
    nome="Switch Intelbras",
    quantidade=10,
    preco=199.90
):
    resposta = cliente_autenticado.post(
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


def criar_movimentacao(
    cliente_autenticado,
    produto_id,
    tipo="ENTRADA",
    quantidade=1
):
    resposta = cliente_autenticado.post(
        "/movimentacoes",
        json={
            "produto_id": produto_id,
            "tipo": tipo,
            "quantidade": quantidade
        }
    )

    assert resposta.status_code == 201

    return resposta


def test_registrar_entrada(cliente_autenticado):
    categoria_id = criar_categoria(cliente_autenticado)

    produto_id = criar_produto(
        cliente_autenticado,
        categoria_id,
        quantidade=10
    )

    resposta = cliente_autenticado.post(
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

    produto = cliente_autenticado.get(
        f"/produtos/{produto_id}"
    )

    assert produto.status_code == 200
    assert produto.json()["quantidade"] == 15


def test_registrar_saida(cliente_autenticado):
    categoria_id = criar_categoria(cliente_autenticado)

    produto_id = criar_produto(
        cliente_autenticado,
        categoria_id,
        quantidade=10
    )

    resposta = cliente_autenticado.post(
        "/movimentacoes",
        json={
            "produto_id": produto_id,
            "tipo": "SAIDA",
            "quantidade": 4
        }
    )

    assert resposta.status_code == 201

    produto = cliente_autenticado.get(
        f"/produtos/{produto_id}"
    )

    assert produto.status_code == 200
    assert produto.json()["quantidade"] == 6


def test_impedir_saida_com_estoque_insuficiente(
    cliente_autenticado
):
    categoria_id = criar_categoria(cliente_autenticado)

    produto_id = criar_produto(
        cliente_autenticado,
        categoria_id,
        quantidade=5
    )

    resposta = cliente_autenticado.post(
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

    produto = cliente_autenticado.get(
        f"/produtos/{produto_id}"
    )

    assert produto.json()["quantidade"] == 5


def test_movimentacao_produto_inexistente(
    cliente_autenticado
):
    resposta = cliente_autenticado.post(
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


def test_listar_movimentacoes(cliente_autenticado):
    categoria_id = criar_categoria(cliente_autenticado)

    produto_id = criar_produto(
        cliente_autenticado,
        categoria_id,
        quantidade=10
    )

    criar_movimentacao(
        cliente_autenticado,
        produto_id,
        tipo="ENTRADA",
        quantidade=5
    )

    criar_movimentacao(
        cliente_autenticado,
        produto_id,
        tipo="SAIDA",
        quantidade=2
    )

    resposta = cliente_autenticado.get(
        "/movimentacoes"
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert len(dados) == 2


def test_buscar_movimentacao_por_id(cliente_autenticado):
    categoria_id = criar_categoria(cliente_autenticado)

    produto_id = criar_produto(
        cliente_autenticado,
        categoria_id
    )

    criacao = criar_movimentacao(
        cliente_autenticado,
        produto_id,
        tipo="ENTRADA",
        quantidade=5
    )

    movimentacao_id = criacao.json()["id"]

    resposta = cliente_autenticado.get(
        f"/movimentacoes/{movimentacao_id}"
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["id"] == movimentacao_id
    assert dados["produto_id"] == produto_id


def test_movimentacao_inexistente(cliente_autenticado):
    resposta = cliente_autenticado.get(
        "/movimentacoes/9999"
    )

    assert resposta.status_code == 404


def test_filtro_movimentacao_por_tipo(cliente_autenticado):
    categoria_id = criar_categoria(cliente_autenticado)

    produto_id = criar_produto(
        cliente_autenticado,
        categoria_id,
        quantidade=20
    )

    criar_movimentacao(
        cliente_autenticado,
        produto_id,
        tipo="ENTRADA",
        quantidade=5
    )

    criar_movimentacao(
        cliente_autenticado,
        produto_id,
        tipo="SAIDA",
        quantidade=3
    )

    resposta = cliente_autenticado.get(
        "/movimentacoes",
        params={
            "tipo": "SAIDA"
        }
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert len(dados) == 1
    assert dados[0]["tipo"] == "SAIDA"


def test_filtro_movimentacao_por_produto(cliente_autenticado):
    categoria_id = criar_categoria(cliente_autenticado)

    produto_1 = criar_produto(
        cliente_autenticado,
        categoria_id,
        nome="Produto 1"
    )

    produto_2 = criar_produto(
        cliente_autenticado,
        categoria_id,
        nome="Produto 2"
    )

    criar_movimentacao(
        cliente_autenticado,
        produto_1,
        tipo="ENTRADA",
        quantidade=5
    )

    criar_movimentacao(
        cliente_autenticado,
        produto_2,
        tipo="ENTRADA",
        quantidade=5
    )

    resposta = cliente_autenticado.get(
        "/movimentacoes",
        params={
            "produto_id": produto_1
        }
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert len(dados) == 1
    assert dados[0]["produto_id"] == produto_1


def test_validacao_tipo_movimentacao(cliente_autenticado):
    categoria_id = criar_categoria(cliente_autenticado)

    produto_id = criar_produto(
        cliente_autenticado,
        categoria_id
    )

    resposta = cliente_autenticado.post(
        "/movimentacoes",
        json={
            "produto_id": produto_id,
            "tipo": "TESTE",
            "quantidade": 5
        }
    )

    assert resposta.status_code == 422


def test_validacao_quantidade_movimentacao(
    cliente_autenticado
):
    categoria_id = criar_categoria(cliente_autenticado)

    produto_id = criar_produto(
        cliente_autenticado,
        categoria_id
    )

    resposta = cliente_autenticado.post(
        "/movimentacoes",
        json={
            "produto_id": produto_id,
            "tipo": "ENTRADA",
            "quantidade": 0
        }
    )

    assert resposta.status_code == 422


def test_paginacao_movimentacoes_primeira_pagina(
    cliente_autenticado
):
    categoria_id = criar_categoria(cliente_autenticado)

    produto_id = criar_produto(
        cliente_autenticado,
        categoria_id,
        quantidade=10
    )

    for quantidade in range(1, 6):
        criar_movimentacao(
            cliente_autenticado,
            produto_id,
            tipo="ENTRADA",
            quantidade=quantidade
        )

    resposta = cliente_autenticado.get(
        "/movimentacoes",
        params={
            "pagina": 1,
            "tamanho": 2
        }
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert len(dados) == 2

    assert dados[0]["quantidade"] == 5
    assert dados[1]["quantidade"] == 4


def test_paginacao_movimentacoes_segunda_pagina(
    cliente_autenticado
):
    categoria_id = criar_categoria(cliente_autenticado)

    produto_id = criar_produto(
        cliente_autenticado,
        categoria_id,
        quantidade=10
    )

    for quantidade in range(1, 6):
        criar_movimentacao(
            cliente_autenticado,
            produto_id,
            tipo="ENTRADA",
            quantidade=quantidade
        )

    resposta = cliente_autenticado.get(
        "/movimentacoes",
        params={
            "pagina": 2,
            "tamanho": 2
        }
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert len(dados) == 2

    assert dados[0]["quantidade"] == 3
    assert dados[1]["quantidade"] == 2


def test_paginacao_movimentacoes_ultima_pagina(
    cliente_autenticado
):
    categoria_id = criar_categoria(cliente_autenticado)

    produto_id = criar_produto(
        cliente_autenticado,
        categoria_id,
        quantidade=10
    )

    for quantidade in range(1, 6):
        criar_movimentacao(
            cliente_autenticado,
            produto_id,
            tipo="ENTRADA",
            quantidade=quantidade
        )

    resposta = cliente_autenticado.get(
        "/movimentacoes",
        params={
            "pagina": 3,
            "tamanho": 2
        }
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert len(dados) == 1
    assert dados[0]["quantidade"] == 1


def test_paginacao_movimentacoes_com_filtro(
    cliente_autenticado
):
    categoria_id = criar_categoria(cliente_autenticado)

    produto_id = criar_produto(
        cliente_autenticado,
        categoria_id,
        quantidade=20
    )

    for quantidade in range(1, 5):
        criar_movimentacao(
            cliente_autenticado,
            produto_id,
            tipo="ENTRADA",
            quantidade=quantidade
        )

    criar_movimentacao(
        cliente_autenticado,
        produto_id,
        tipo="SAIDA",
        quantidade=1
    )

    resposta = cliente_autenticado.get(
        "/movimentacoes",
        params={
            "tipo": "ENTRADA",
            "pagina": 2,
            "tamanho": 2
        }
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert len(dados) == 2

    assert dados[0]["tipo"] == "ENTRADA"
    assert dados[1]["tipo"] == "ENTRADA"

    assert dados[0]["quantidade"] == 2
    assert dados[1]["quantidade"] == 1


def test_validacao_pagina_movimentacoes(cliente_autenticado):
    resposta = cliente_autenticado.get(
        "/movimentacoes",
        params={
            "pagina": 0
        }
    )

    assert resposta.status_code == 422


def test_validacao_tamanho_pagina_movimentacoes(
    cliente_autenticado
):
    resposta = cliente_autenticado.get(
        "/movimentacoes",
        params={
            "tamanho": 101
        }
    )

    assert resposta.status_code == 422

def test_movimentacao_registra_usuario(cliente_autenticado):
    categoria_id = criar_categoria(cliente_autenticado)

    produto_id = criar_produto(
        cliente_autenticado,
        categoria_id
    )

    criada = criar_movimentacao(
        cliente_autenticado,
        produto_id
    ).json()

    assert criada["usuario"] == "Usuario Testes"
    assert criada["usuario_id"] is not None

    listada = cliente_autenticado.get(
        "/movimentacoes"
    ).json()[0]

    assert listada["usuario"] == "Usuario Testes"
