import uuid

from backend.tests.apoio_compras import (
    criar_fornecedor,
    criar_solicitacao_com_dois_itens,
    registrar_cotacao,
)


def codigo_unico():
    return "T" + uuid.uuid4().hex[:6]


def criar_forma(cliente, **dados):
    corpo = {
        "codigo": codigo_unico(),
        "titulo": "Teste 30/60",
        "tipo": "A_PRAZO",
        "parcelas": 2,
        "intervalo_dias": 30,
        **dados,
    }

    return cliente.post("/formas-pagamento", json=corpo)


def forma_padrao(cliente, codigo):
    resposta = cliente.get(f"/formas-pagamento?busca={codigo}").json()
    return next(f for f in resposta["itens"] if f["codigo"] == codigo)


def test_formas_padrao(cliente_autenticado):
    resposta = cliente_autenticado.get("/formas-pagamento?tamanho=100")

    assert resposta.status_code == 200

    dados = resposta.json()
    por_codigo = {f["codigo"]: f for f in dados["itens"]}

    assert dados["total"] >= 14
    assert dados["itens"][0]["codigo"] == "1.01"
    assert por_codigo["1.01"]["tipo"] == "A_VISTA"
    assert por_codigo["2.01"]["titulo"] == "Dia específico"
    assert por_codigo["3.12"]["parcelas"] == 12
    assert por_codigo["3.03"]["intervalo_dias"] == 30


def test_busca_ordenacao_e_paginacao(cliente_autenticado):
    cliente = cliente_autenticado

    busca = cliente.get("/formas-pagamento?busca=prazo%201").json()
    titulos = {f["titulo"] for f in busca["itens"]}

    assert {"A prazo 1X", "A prazo 10X", "A prazo 11X", "A prazo 12X"} <= titulos
    assert busca["total"] == len(busca["itens"])

    a_vista = cliente.get("/formas-pagamento?tipo=A_VISTA").json()
    assert all(f["tipo"] == "A_VISTA" for f in a_vista["itens"])

    decrescente = cliente.get(
        "/formas-pagamento?busca=A%20prazo&ordem=codigo&decrescente=true"
    ).json()
    codigos = [f["codigo"] for f in decrescente["itens"]]
    assert codigos == sorted(codigos, reverse=True)

    pagina_1 = cliente.get("/formas-pagamento?tamanho=5&pagina=1").json()
    pagina_2 = cliente.get("/formas-pagamento?tamanho=5&pagina=2").json()

    assert len(pagina_1["itens"]) == 5
    assert pagina_1["total"] == pagina_2["total"]
    assert pagina_1["itens"][0]["id"] != pagina_2["itens"][0]["id"]


def test_criar_editar_e_inativar(cliente_autenticado):
    cliente = cliente_autenticado

    criada = criar_forma(cliente)

    assert criada.status_code == 201

    forma = criada.json()

    assert forma["ativo"] is True

    editada = cliente.put(
        f"/formas-pagamento/{forma['id']}",
        json={
            "codigo": forma["codigo"],
            "titulo": "Teste 28 dias",
            "tipo": "A_PRAZO",
            "parcelas": 1,
            "intervalo_dias": 28
        }
    )

    assert editada.status_code == 200
    assert editada.json()["titulo"] == "Teste 28 dias"

    inativada = cliente.patch(
        f"/formas-pagamento/{forma['id']}/status",
        json={"ativo": False}
    )

    assert inativada.status_code == 200
    assert inativada.json()["ativo"] is False

    inativas = cliente.get(
        f"/formas-pagamento?ativo=false&busca={forma['codigo']}"
    ).json()

    assert [f["id"] for f in inativas["itens"]] == [forma["id"]]


def test_codigo_duplicado(cliente_autenticado):
    codigo = codigo_unico()

    assert criar_forma(cliente_autenticado, codigo=codigo).status_code == 201

    resposta = criar_forma(cliente_autenticado, codigo=codigo)

    assert resposta.status_code == 409
    assert resposta.json() == {
        "detail": "Já existe uma forma de pagamento com esse código."
    }


def test_validacoes(cliente_autenticado):
    a_vista_parcelada = criar_forma(
        cliente_autenticado,
        tipo="A_VISTA",
        parcelas=3
    )
    codigo_invalido = criar_forma(cliente_autenticado, codigo="1 01")
    tipo_invalido = criar_forma(cliente_autenticado, tipo="BOLETO")

    assert a_vista_parcelada.status_code == 422
    assert codigo_invalido.status_code == 422
    assert tipo_invalido.status_code == 422


def test_forma_inexistente(cliente_autenticado):
    cliente = cliente_autenticado

    assert cliente.get("/formas-pagamento/999999").status_code == 404

    resposta = cliente.patch(
        "/formas-pagamento/999999/status",
        json={"ativo": False}
    )

    assert resposta.status_code == 404


def test_cotacao_e_compra_com_forma_de_pagamento(cliente_autenticado):
    cliente = cliente_autenticado
    solicitacao_id, cabo, conector = criar_solicitacao_com_dois_itens(cliente)
    fornecedor_id = criar_fornecedor(cliente, "Fornecedor Pagamento")
    forma = forma_padrao(cliente, "3.03")

    resposta = cliente.post(
        f"/solicitacoes-compra/{solicitacao_id}/cotacoes",
        json={
            "fornecedor_id": fornecedor_id,
            "prazo_entrega_dias": 5,
            "validade": "2099-12-31",
            "forma_pagamento_id": forma["id"],
            "itens": [
                {"produto_id": cabo, "preco_unitario": 2},
                {"produto_id": conector, "preco_unitario": 1}
            ]
        }
    )

    assert resposta.status_code == 201

    cotacao = resposta.json()

    assert cotacao["forma_pagamento_id"] == forma["id"]
    assert cotacao["forma_pagamento"] == "3.03 - A prazo 3X"

    comparacao = cliente.get(
        f"/solicitacoes-compra/{solicitacao_id}/cotacoes/comparacao"
    ).json()

    assert comparacao["cotacoes"][0]["forma_pagamento"] == "3.03 - A prazo 3X"
    assert comparacao["menor_valor_total"]["forma_pagamento"] == "3.03 - A prazo 3X"

    cliente.patch(
        f"/solicitacoes-compra/{solicitacao_id}/aprovar",
        json={"cotacao_id": cotacao["id"]}
    )

    compra = cliente.post(
        f"/solicitacoes-compra/{solicitacao_id}/compra",
        json={}
    ).json()

    assert compra["forma_pagamento_id"] == forma["id"]
    assert compra["forma_pagamento"] == "3.03 - A prazo 3X"


def test_cotacao_com_forma_inexistente_ou_inativa(cliente_autenticado):
    cliente = cliente_autenticado
    solicitacao_id, cabo, _ = criar_solicitacao_com_dois_itens(cliente)
    fornecedor_id = criar_fornecedor(cliente, "Fornecedor Pagamento")
    inativa = criar_forma(cliente).json()

    cliente.patch(
        f"/formas-pagamento/{inativa['id']}/status",
        json={"ativo": False}
    )

    def cotar(forma_id):
        return cliente.post(
            f"/solicitacoes-compra/{solicitacao_id}/cotacoes",
            json={
                "fornecedor_id": fornecedor_id,
                "prazo_entrega_dias": 5,
                "forma_pagamento_id": forma_id,
                "itens": [{"produto_id": cabo, "preco_unitario": 2}]
            }
        )

    inexistente = cotar(999999)
    desativada = cotar(inativa["id"])

    assert inexistente.status_code == 404
    assert inexistente.json() == {"detail": "Forma de pagamento não encontrada."}
    assert desativada.status_code == 400
    assert desativada.json() == {"detail": "Forma de pagamento inativa."}


def test_editar_cotacao_mantendo_forma_inativa(cliente_autenticado):
    cliente = cliente_autenticado
    solicitacao_id, cabo, _ = criar_solicitacao_com_dois_itens(cliente)
    fornecedor_id = criar_fornecedor(cliente, "Fornecedor Pagamento")
    forma = criar_forma(cliente).json()

    cotacao = registrar_cotacao(
        cliente, solicitacao_id, fornecedor_id, {cabo: 2}
    )

    url = f"/solicitacoes-compra/{solicitacao_id}/cotacoes/{cotacao['id']}"
    corpo = {
        "prazo_entrega_dias": 5,
        "forma_pagamento_id": forma["id"],
        "itens": [{"produto_id": cabo, "preco_unitario": 2}]
    }

    assert cliente.put(url, json=corpo).status_code == 200

    cliente.patch(
        f"/formas-pagamento/{forma['id']}/status",
        json={"ativo": False}
    )

    corpo["itens"][0]["preco_unitario"] = 3

    resposta = cliente.put(url, json=corpo)

    assert resposta.status_code == 200
    assert resposta.json()["forma_pagamento_id"] == forma["id"]
