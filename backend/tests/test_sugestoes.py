from backend.database import conectar
from backend.tests.apoio_compras import compra_registrada, criar_produto


def produto(cliente, nome, quantidade, minimo):
    categoria = cliente.post("/categorias", json={"nome": f"Categoria {nome}"}).json()["id"]
    resposta = cliente.post("/produtos", json={
        "nome": nome, "categoria_id": categoria, "quantidade": quantidade,
        "preco": 10, "estoque_minimo": minimo,
    })
    assert resposta.status_code == 201
    return resposta.json()["id"]


def saida(cliente, produto_id, quantidade, dias_atras=0):
    resposta = cliente.post("/movimentacoes", json={"produto_id": produto_id, "tipo": "SAIDA", "quantidade": quantidade})
    assert resposta.status_code == 201
    if dias_atras:
        conexao = conectar()
        cursor = conexao.cursor()
        cursor.execute(
            "UPDATE movimentacoes SET data_movimentacao = CURRENT_TIMESTAMP - make_interval(days => %s) WHERE id = %s;",
            (dias_atras, resposta.json()["id"]),
        )
        conexao.commit()
        conexao.close()


def por_nome(dados):
    return {item["produto"]: item for item in dados}


def test_sugere_pelo_minimo_e_pelo_consumo(cliente_autenticado):
    abaixo = produto(cliente_autenticado, "Abaixo do mínimo", 3, 5)
    giro = produto(cliente_autenticado, "Giro alto", 200, 10)
    parado = produto(cliente_autenticado, "Parado", 50, 5)

    # 180 unidades em 90 dias = 2 por dia; sobra 20, que dura 10 dias (prazo padrão 7)
    saida(cliente_autenticado, giro, 180, dias_atras=10)
    # Consumo antigo, fora do período, não conta
    saida(cliente_autenticado, parado, 40, dias_atras=200)

    resposta = cliente_autenticado.get("/sugestoes-compra")

    assert resposta.status_code == 200
    dados = por_nome(resposta.json())
    assert set(dados) == {"Abaixo do mínimo", "Giro alto"}
    assert resposta.json()[0]["produto"] == "Abaixo do mínimo"

    assert dados["Abaixo do mínimo"]["sugerido"] == 5
    assert dados["Abaixo do mínimo"]["prazo_estimado"] is True

    item = dados["Giro alto"]
    assert item["consumo_mensal"] == 60
    assert item["dias_restantes"] == 10
    assert item["ponto_pedido"] == 24
    # alvo = 10 + 2 × (7 + 30) = 84 → comprar 64
    assert item["sugerido"] == 64
    assert item["valor_estimado"] == 640

    todos = por_nome(cliente_autenticado.get("/sugestoes-compra?todos=true").json())
    assert todos["Parado"]["sugerido"] == 0
    assert todos["Parado"]["consumo_periodo"] == 0

    menos_cobertura = por_nome(cliente_autenticado.get("/sugestoes-compra?cobertura_dias=0").json())
    assert menos_cobertura["Giro alto"]["sugerido"] == 10


def test_pedido_aberto_e_compra_a_receber_contam(cliente_autenticado):
    _, compra = compra_registrada(cliente_autenticado)
    cabo = compra["itens"][0]["produto_id"]

    sugestoes = por_nome(cliente_autenticado.get("/sugestoes-compra?todos=true").json())
    cabo_nome = next(nome for nome, item in sugestoes.items() if item["produto_id"] == cabo)

    assert sugestoes[cabo_nome]["em_pedido"] == compra["itens"][0]["quantidade"]
    assert sugestoes[cabo_nome]["prazo_estimado"] is False
    assert sugestoes[cabo_nome]["ultimo_fornecedor"] == "Fornecedor Aprovado"

    avulso = criar_produto(cliente_autenticado, "Avulso")
    antes = por_nome(cliente_autenticado.get("/sugestoes-compra").json())
    assert "Avulso" in antes

    cliente_autenticado.post("/solicitacoes-compra", json={"itens": [{"produto_id": avulso, "quantidade": 10}]})
    depois = por_nome(cliente_autenticado.get("/sugestoes-compra").json())
    assert "Avulso" not in depois


def test_parametros_validados(cliente_autenticado):
    assert cliente_autenticado.get("/sugestoes-compra?dias_consumo=1").status_code == 422


def test_estoque_minimo_zero_e_compra_avulsa(cliente_autenticado):
    produto(cliente_autenticado, "Avulso", 0, 0)
    consumido = produto(cliente_autenticado, "Avulso consumido", 30, 0)
    saida(cliente_autenticado, consumido, 30, dias_atras=5)

    assert cliente_autenticado.get("/sugestoes-compra").json() == []

    todos = por_nome(cliente_autenticado.get("/sugestoes-compra?todos=true").json())
    assert todos["Avulso consumido"]["sugerido"] == 0
    assert todos["Avulso consumido"]["motivo"] is None
