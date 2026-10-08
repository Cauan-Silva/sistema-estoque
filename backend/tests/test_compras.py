from datetime import date, timedelta

from backend.tests.apoio_compras import (
    criar_solicitacao_com_dois_itens,
    solicitacao_aprovada,
)


def registrar(cliente, solicitacao_id, **dados):
    return cliente.post(
        f"/solicitacoes-compra/{solicitacao_id}/compra",
        json=dados
    )


def test_registrar_compra(cliente_autenticado):
    cliente = cliente_autenticado
    solicitacao_id, cotacao = solicitacao_aprovada(cliente)

    resposta = registrar(
        cliente,
        solicitacao_id,
        numero_pedido="PED-001",
        data_compra="2026-10-01",
        observacao="Pago via boleto"
    )

    assert resposta.status_code == 201

    dados = resposta.json()

    assert dados["solicitacao_id"] == solicitacao_id
    assert dados["cotacao_id"] == cotacao["id"]
    assert dados["fornecedor"] == "Fornecedor Aprovado"
    assert dados["comprador"] == "Usuario Testes"
    assert dados["numero_pedido"] == "PED-001"
    assert dados["data_compra"] == "2026-10-01"
    assert dados["previsao_entrega"] == "2026-10-11"
    assert dados["valor_itens"] == 30.0
    assert dados["frete"] == 12.0
    assert dados["valor_total"] == 42.0
    assert [
        (i["quantidade"], i["preco_unitario"], i["subtotal"])
        for i in dados["itens"]
    ] == [
        (10, 2.5, 25.0),
        (4, 1.25, 5.0)
    ]

    solicitacao = cliente.get(
        f"/solicitacoes-compra/{solicitacao_id}"
    ).json()

    assert solicitacao["status"] == "COMPRADA"


def test_registrar_compra_com_datas_padrao(cliente_autenticado):
    solicitacao_id, _ = solicitacao_aprovada(cliente_autenticado)

    dados = registrar(cliente_autenticado, solicitacao_id).json()

    hoje = date.today()

    assert dados["data_compra"] == hoje.isoformat()
    assert dados["previsao_entrega"] == (
        hoje + timedelta(days=10)
    ).isoformat()


def test_nao_registrar_compra_sem_aprovacao(cliente_autenticado):
    solicitacao_id, _, _ = criar_solicitacao_com_dois_itens(
        cliente_autenticado
    )

    resposta = registrar(cliente_autenticado, solicitacao_id)

    assert resposta.status_code == 409
    assert resposta.json() == {
        "detail": (
            "Apenas solicitações aprovadas podem ter a compra registrada."
        )
    }


def test_nao_registrar_compra_duas_vezes(cliente_autenticado):
    solicitacao_id, _ = solicitacao_aprovada(cliente_autenticado)

    primeira = registrar(cliente_autenticado, solicitacao_id)
    segunda = registrar(cliente_autenticado, solicitacao_id)

    assert primeira.status_code == 201
    assert segunda.status_code == 409


def test_compra_bloqueia_cancelamento(cliente_autenticado):
    solicitacao_id, _ = solicitacao_aprovada(cliente_autenticado)

    registrar(cliente_autenticado, solicitacao_id)

    resposta = cliente_autenticado.patch(
        f"/solicitacoes-compra/{solicitacao_id}/cancelar"
    )

    assert resposta.status_code == 409


def test_previsao_anterior_a_data_da_compra(cliente_autenticado):
    solicitacao_id, _ = solicitacao_aprovada(cliente_autenticado)

    resposta = registrar(
        cliente_autenticado,
        solicitacao_id,
        data_compra="2026-10-10",
        previsao_entrega="2026-10-01"
    )

    assert resposta.status_code == 422


def test_compra_solicitacao_inexistente(cliente_autenticado):
    resposta = registrar(cliente_autenticado, 9999)

    assert resposta.status_code == 404


def test_consultar_compras(cliente_autenticado):
    cliente = cliente_autenticado
    solicitacao_id, cotacao = solicitacao_aprovada(cliente)

    compra = registrar(cliente, solicitacao_id).json()

    da_solicitacao = cliente.get(
        f"/solicitacoes-compra/{solicitacao_id}/compra"
    )
    por_id = cliente.get(f"/compras/{compra['id']}")
    lista = cliente.get("/compras")
    do_fornecedor = cliente.get(
        f"/compras?fornecedor_id={cotacao['fornecedor_id']}"
    )
    de_outro_fornecedor = cliente.get(
        f"/compras?fornecedor_id={cotacao['fornecedor_id'] + 100}"
    )

    assert da_solicitacao.json() == compra
    assert por_id.json() == compra
    assert lista.json() == [compra]
    assert do_fornecedor.json() == [compra]
    assert de_outro_fornecedor.json() == []


def test_compra_inexistente(cliente_autenticado):
    assert cliente_autenticado.get("/compras/9999").status_code == 404

    solicitacao_id, _, _ = criar_solicitacao_com_dois_itens(
        cliente_autenticado
    )

    resposta = cliente_autenticado.get(
        f"/solicitacoes-compra/{solicitacao_id}/compra"
    )

    assert resposta.status_code == 404
