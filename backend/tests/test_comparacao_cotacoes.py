from backend.tests.apoio_compras import (
    VALIDADE_VENCIDA,
    criar_fornecedor,
    criar_solicitacao_com_dois_itens,
    registrar_cotacao,
)


def test_comparar_cotacoes(cliente_autenticado):
    cliente = cliente_autenticado
    solicitacao_id, cabo, conector = criar_solicitacao_com_dois_itens(cliente)

    f1 = criar_fornecedor(cliente, "F1 Rapido")
    f2 = criar_fornecedor(cliente, "F2 Barato")
    f3 = criar_fornecedor(cliente, "F3 Parcial")
    f4 = criar_fornecedor(cliente, "F4 Vencido")

    c1 = registrar_cotacao(
        cliente, solicitacao_id, f1,
        {cabo: 2.0, conector: 1.0}, frete=10, prazo=2
    )
    c2 = registrar_cotacao(
        cliente, solicitacao_id, f2,
        {cabo: 1.8, conector: 1.5}, frete=0, prazo=3
    )
    c3 = registrar_cotacao(
        cliente, solicitacao_id, f3,
        {cabo: 1.0}, frete=0, prazo=1
    )
    c4 = registrar_cotacao(
        cliente, solicitacao_id, f4,
        {cabo: 1.5, conector: 0.5}, prazo=1,
        validade=VALIDADE_VENCIDA
    )

    resposta = cliente.get(
        f"/solicitacoes-compra/{solicitacao_id}/cotacoes/comparacao"
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["total_cotacoes"] == 4
    assert dados["cotacoes_elegiveis"] == 2

    assert dados["menor_valor_total"]["cotacao_id"] == c2["id"]
    assert dados["menor_valor_total"]["valor_total"] == 24.0
    assert dados["menor_prazo"]["cotacao_id"] == c1["id"]
    assert dados["menor_frete"]["cotacao_id"] == c2["id"]

    assert [c["cotacao_id"] for c in dados["cotacoes"]] == [
        c2["id"], c1["id"], c3["id"], c4["id"]
    ]

    por_id = {c["cotacao_id"]: c for c in dados["cotacoes"]}

    assert por_id[c1["id"]]["valor_total"] == 34.0
    assert por_id[c3["id"]]["cobre_todos_itens"] is False
    assert por_id[c3["id"]]["elegivel"] is False
    assert por_id[c4["id"]]["vencida"] is True
    assert por_id[c4["id"]]["elegivel"] is False

    por_produto = {p["produto_id"]: p for p in dados["por_produto"]}

    assert por_produto[cabo]["melhor_preco_unitario"] == 1.0
    assert por_produto[cabo]["fornecedor"] == "F3 Parcial"
    assert por_produto[cabo]["quantidade_ofertas"] == 3
    assert por_produto[conector]["melhor_preco_unitario"] == 1.0
    assert por_produto[conector]["fornecedor"] == "F1 Rapido"
    assert por_produto[conector]["quantidade_ofertas"] == 2


def test_comparar_sem_cotacoes(cliente_autenticado):
    solicitacao_id, _, _ = criar_solicitacao_com_dois_itens(
        cliente_autenticado
    )

    dados = cliente_autenticado.get(
        f"/solicitacoes-compra/{solicitacao_id}/cotacoes/comparacao"
    ).json()

    assert dados["total_cotacoes"] == 0
    assert dados["menor_valor_total"] is None
    assert dados["menor_prazo"] is None
    assert dados["cotacoes"] == []
    assert all(
        p["melhor_preco_unitario"] is None
        for p in dados["por_produto"]
    )


def test_comparar_solicitacao_inexistente(cliente_autenticado):
    resposta = cliente_autenticado.get(
        "/solicitacoes-compra/9999/cotacoes/comparacao"
    )

    assert resposta.status_code == 404
