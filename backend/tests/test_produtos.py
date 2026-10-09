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

    return resposta


def test_criar_produto(cliente_autenticado):
    categoria_id = criar_categoria(cliente_autenticado)

    resposta = criar_produto(
        cliente_autenticado,
        categoria_id
    )

    dados = resposta.json()

    assert dados["id"] == 1
    assert dados["nome"] == "Switch Intelbras"
    assert dados["categoria_id"] == categoria_id
    assert dados["categoria"] == "Switches"
    assert dados["quantidade"] == 10
    assert dados["preco"] == 199.90


def test_listar_produtos(cliente_autenticado):
    categoria_id = criar_categoria(cliente_autenticado)

    criar_produto(
        cliente_autenticado,
        categoria_id,
        nome="Switch 8 Portas"
    )

    criar_produto(
        cliente_autenticado,
        categoria_id,
        nome="Switch 16 Portas"
    )

    resposta = cliente_autenticado.get(
        "/produtos"
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert len(dados) == 2


def test_buscar_produto_por_id(cliente_autenticado):
    categoria_id = criar_categoria(cliente_autenticado)

    criacao = criar_produto(
        cliente_autenticado,
        categoria_id
    )

    produto_id = criacao.json()["id"]

    resposta = cliente_autenticado.get(
        f"/produtos/{produto_id}"
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["id"] == produto_id
    assert dados["nome"] == "Switch Intelbras"


def test_produto_inexistente(cliente_autenticado):
    resposta = cliente_autenticado.get(
        "/produtos/9999"
    )

    assert resposta.status_code == 404

    assert resposta.json() == {
        "detail": "Produto não encontrado."
    }


def test_categoria_inexistente_ao_criar_produto(cliente_autenticado):
    resposta = cliente_autenticado.post(
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


def test_atualizar_produto(cliente_autenticado):
    categoria_id = criar_categoria(cliente_autenticado)

    criacao = criar_produto(
        cliente_autenticado,
        categoria_id
    )

    produto_id = criacao.json()["id"]

    resposta = cliente_autenticado.put(
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


def test_excluir_produto(cliente_autenticado):
    categoria_id = criar_categoria(cliente_autenticado)

    criacao = criar_produto(
        cliente_autenticado,
        categoria_id
    )

    produto_id = criacao.json()["id"]

    resposta = cliente_autenticado.delete(
        f"/produtos/{produto_id}"
    )

    assert resposta.status_code == 204

    consulta = cliente_autenticado.get(
        f"/produtos/{produto_id}"
    )

    assert consulta.status_code == 404


def test_busca_produto_por_nome(cliente_autenticado):
    categoria_id = criar_categoria(cliente_autenticado)

    criar_produto(
        cliente_autenticado,
        categoria_id,
        nome="Switch Intelbras"
    )

    criar_produto(
        cliente_autenticado,
        categoria_id,
        nome="Roteador TP-Link"
    )

    resposta = cliente_autenticado.get(
        "/produtos",
        params={
            "busca": "Intelbras"
        }
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert len(dados) == 1
    assert dados[0]["nome"] == "Switch Intelbras"


def test_filtro_produto_por_categoria(cliente_autenticado):
    categoria_switch = criar_categoria(
        cliente_autenticado,
        "Switches"
    )

    categoria_roteador = criar_categoria(
        cliente_autenticado,
        "Roteadores"
    )

    criar_produto(
        cliente_autenticado,
        categoria_switch,
        nome="Switch Intelbras"
    )

    criar_produto(
        cliente_autenticado,
        categoria_roteador,
        nome="Roteador Intelbras"
    )

    resposta = cliente_autenticado.get(
        "/produtos",
        params={
            "categoria_id": categoria_switch
        }
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert len(dados) == 1
    assert dados[0]["categoria"] == "Switches"


def test_filtro_estoque_baixo(cliente_autenticado):
    categoria_id = criar_categoria(cliente_autenticado)

    criar_produto(
        cliente_autenticado,
        categoria_id,
        nome="Produto Estoque Baixo",
        quantidade=3
    )

    criar_produto(
        cliente_autenticado,
        categoria_id,
        nome="Produto Estoque Alto",
        quantidade=20
    )

    resposta = cliente_autenticado.get(
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


def test_validacao_produto(cliente_autenticado):
    categoria_id = criar_categoria(cliente_autenticado)

    resposta = cliente_autenticado.post(
        "/produtos",
        json={
            "nome": "A",
            "categoria_id": categoria_id,
            "quantidade": -1,
            "preco": -10
        }
    )

    assert resposta.status_code == 422


def test_paginacao_produtos_primeira_pagina(cliente_autenticado):
    categoria_id = criar_categoria(cliente_autenticado)

    for numero in range(1, 6):
        criar_produto(
            cliente_autenticado,
            categoria_id,
            nome=f"Produto {numero}"
        )

    resposta = cliente_autenticado.get(
        "/produtos",
        params={
            "pagina": 1,
            "tamanho": 2
        }
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert len(dados) == 2
    assert dados[0]["nome"] == "Produto 1"
    assert dados[1]["nome"] == "Produto 2"


def test_paginacao_produtos_segunda_pagina(cliente_autenticado):
    categoria_id = criar_categoria(cliente_autenticado)

    for numero in range(1, 6):
        criar_produto(
            cliente_autenticado,
            categoria_id,
            nome=f"Produto {numero}"
        )

    resposta = cliente_autenticado.get(
        "/produtos",
        params={
            "pagina": 2,
            "tamanho": 2
        }
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert len(dados) == 2
    assert dados[0]["nome"] == "Produto 3"
    assert dados[1]["nome"] == "Produto 4"


def test_paginacao_produtos_ultima_pagina(cliente_autenticado):
    categoria_id = criar_categoria(cliente_autenticado)

    for numero in range(1, 6):
        criar_produto(
            cliente_autenticado,
            categoria_id,
            nome=f"Produto {numero}"
        )

    resposta = cliente_autenticado.get(
        "/produtos",
        params={
            "pagina": 3,
            "tamanho": 2
        }
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert len(dados) == 1
    assert dados[0]["nome"] == "Produto 5"


def test_paginacao_produtos_com_filtro(cliente_autenticado):
    categoria_switch = criar_categoria(
        cliente_autenticado,
        "Switches"
    )

    categoria_roteador = criar_categoria(
        cliente_autenticado,
        "Roteadores"
    )

    for numero in range(1, 5):
        criar_produto(
            cliente_autenticado,
            categoria_switch,
            nome=f"Switch {numero}"
        )

    criar_produto(
        cliente_autenticado,
        categoria_roteador,
        nome="Roteador 1"
    )

    resposta = cliente_autenticado.get(
        "/produtos",
        params={
            "categoria_id": categoria_switch,
            "pagina": 2,
            "tamanho": 2
        }
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert len(dados) == 2
    assert dados[0]["nome"] == "Switch 3"
    assert dados[1]["nome"] == "Switch 4"


def test_validacao_pagina_produtos(cliente_autenticado):
    resposta = cliente_autenticado.get(
        "/produtos",
        params={
            "pagina": 0
        }
    )

    assert resposta.status_code == 422


def test_validacao_tamanho_pagina_produtos(cliente_autenticado):
    resposta = cliente_autenticado.get(
        "/produtos",
        params={
            "tamanho": 101
        }
    )

    assert resposta.status_code == 422

def criar_fornecedor(cliente_autenticado, nome="Fornecedor Produtos"):
    resposta = cliente_autenticado.post(
        "/fornecedores",
        json={
            "nome": nome
        }
    )

    assert resposta.status_code == 201

    return resposta.json()["id"]


def test_produto_sem_fornecedor(cliente_autenticado):
    categoria_id = criar_categoria(cliente_autenticado)

    dados = criar_produto(
        cliente_autenticado,
        categoria_id
    ).json()

    assert dados["fornecedor_id"] is None
    assert dados["fornecedor"] is None


def test_criar_produto_com_fornecedor(cliente_autenticado):
    categoria_id = criar_categoria(cliente_autenticado)
    fornecedor_id = criar_fornecedor(cliente_autenticado)

    resposta = cliente_autenticado.post(
        "/produtos",
        json={
            "nome": "Roteador",
            "categoria_id": categoria_id,
            "quantidade": 5,
            "preco": 150,
            "fornecedor_id": fornecedor_id
        }
    )

    assert resposta.status_code == 201

    dados = resposta.json()

    assert dados["fornecedor_id"] == fornecedor_id
    assert dados["fornecedor"] == "Fornecedor Produtos"


def test_criar_produto_com_fornecedor_inexistente(cliente_autenticado):
    categoria_id = criar_categoria(cliente_autenticado)

    resposta = cliente_autenticado.post(
        "/produtos",
        json={
            "nome": "Roteador",
            "categoria_id": categoria_id,
            "quantidade": 5,
            "preco": 150,
            "fornecedor_id": 9999
        }
    )

    assert resposta.status_code == 404

    assert resposta.json() == {
        "detail": "Fornecedor não encontrado."
    }


def test_criar_produto_com_fornecedor_inativo(cliente_autenticado):
    categoria_id = criar_categoria(cliente_autenticado)
    fornecedor_id = criar_fornecedor(cliente_autenticado)

    cliente_autenticado.patch(
        f"/fornecedores/{fornecedor_id}/status",
        json={
            "ativo": False
        }
    )

    resposta = cliente_autenticado.post(
        "/produtos",
        json={
            "nome": "Roteador",
            "categoria_id": categoria_id,
            "quantidade": 5,
            "preco": 150,
            "fornecedor_id": fornecedor_id
        }
    )

    assert resposta.status_code == 400

    assert resposta.json() == {
        "detail": "Fornecedor inativo."
    }


def test_editar_produto_mantendo_fornecedor_inativo(cliente_autenticado):
    categoria_id = criar_categoria(cliente_autenticado)
    fornecedor_id = criar_fornecedor(cliente_autenticado)

    produto = cliente_autenticado.post(
        "/produtos",
        json={
            "nome": "Roteador",
            "categoria_id": categoria_id,
            "quantidade": 5,
            "preco": 150,
            "fornecedor_id": fornecedor_id
        }
    ).json()

    cliente_autenticado.patch(
        f"/fornecedores/{fornecedor_id}/status",
        json={
            "ativo": False
        }
    )

    resposta = cliente_autenticado.put(
        f"/produtos/{produto['id']}",
        json={
            "nome": "Roteador Wi-Fi 6",
            "categoria_id": categoria_id,
            "quantidade": 8,
            "preco": 180,
            "fornecedor_id": fornecedor_id
        }
    )

    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Roteador Wi-Fi 6"
    assert resposta.json()["fornecedor_id"] == fornecedor_id


def test_filtrar_produtos_por_fornecedor(cliente_autenticado):
    categoria_id = criar_categoria(cliente_autenticado)
    fornecedor_a = criar_fornecedor(cliente_autenticado, "Fornecedor A")
    fornecedor_b = criar_fornecedor(cliente_autenticado, "Fornecedor B")

    for nome, fornecedor_id in [
        ("Produto A", fornecedor_a),
        ("Produto B", fornecedor_b),
        ("Produto Sem Fornecedor", None),
    ]:
        cliente_autenticado.post(
            "/produtos",
            json={
                "nome": nome,
                "categoria_id": categoria_id,
                "quantidade": 1,
                "preco": 10,
                "fornecedor_id": fornecedor_id
            }
        )

    resposta = cliente_autenticado.get(
        f"/produtos?fornecedor_id={fornecedor_a}"
    )

    assert resposta.status_code == 200

    nomes = [produto["nome"] for produto in resposta.json()]

    assert nomes == ["Produto A"]


def test_estoque_minimo_por_produto(cliente_autenticado):
    categoria_id = criar_categoria(cliente_autenticado)

    padrao = criar_produto(
        cliente_autenticado,
        categoria_id,
        nome="Mínimo padrão",
        quantidade=8
    ).json()

    assert padrao["estoque_minimo"] == 5

    resposta = cliente_autenticado.post(
        "/produtos",
        json={
            "nome": "Mínimo dez",
            "categoria_id": categoria_id,
            "quantidade": 8,
            "preco": 10,
            "estoque_minimo": 10
        }
    )

    assert resposta.status_code == 201
    assert resposta.json()["estoque_minimo"] == 10

    baixos = cliente_autenticado.get(
        "/produtos",
        params={"estoque_baixo": True}
    ).json()

    assert [p["nome"] for p in baixos] == ["Mínimo dez"]

    resumo = cliente_autenticado.get(
        "/relatorios/resumo"
    ).json()

    assert resumo["produtos_estoque_baixo"] == 1
