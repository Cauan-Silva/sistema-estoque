from backend.tests.apoio_compras import (
    VALIDADE_VENCIDA,
    criar_fornecedor,
    criar_solicitacao_com_dois_itens,
    registrar_cotacao,
    solicitacao_aprovada,
)


def aprovar(cliente, solicitacao_id, cotacao_id, justificativa=None):
    return cliente.patch(
        f"/solicitacoes-compra/{solicitacao_id}/aprovar",
        json={
            "cotacao_id": cotacao_id,
            "justificativa": justificativa
        }
    )


def test_aprovar_cotacao(cliente_autenticado):
    cliente = cliente_autenticado
    solicitacao_id, cabo, conector = criar_solicitacao_com_dois_itens(cliente)
    fornecedor_id = criar_fornecedor(cliente, "Fornecedor A")

    cotacao = registrar_cotacao(
        cliente, solicitacao_id, fornecedor_id,
        {cabo: 2, conector: 1}
    )

    resposta = aprovar(
        cliente,
        solicitacao_id,
        cotacao["id"],
        "Menor valor total"
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["status"] == "APROVADA"
    assert dados["cotacao_aprovada_id"] == cotacao["id"]
    assert dados["decisao_por"] == "Usuario Testes"
    assert dados["data_decisao"] is not None
    assert dados["justificativa_decisao"] == "Menor valor total"


def test_nao_aprovar_cotacao_incompleta(cliente_autenticado):
    cliente = cliente_autenticado
    solicitacao_id, cabo, _ = criar_solicitacao_com_dois_itens(cliente)
    fornecedor_id = criar_fornecedor(cliente, "Fornecedor A")

    cotacao = registrar_cotacao(
        cliente, solicitacao_id, fornecedor_id, {cabo: 2}
    )

    resposta = aprovar(cliente, solicitacao_id, cotacao["id"])

    assert resposta.status_code == 400
    assert resposta.json() == {
        "detail": "A cotação não cobre todos os itens da solicitação."
    }


def test_nao_aprovar_cotacao_vencida(cliente_autenticado):
    cliente = cliente_autenticado
    solicitacao_id, cabo, conector = criar_solicitacao_com_dois_itens(cliente)
    fornecedor_id = criar_fornecedor(cliente, "Fornecedor A")

    cotacao = registrar_cotacao(
        cliente, solicitacao_id, fornecedor_id,
        {cabo: 2, conector: 1},
        validade=VALIDADE_VENCIDA
    )

    resposta = aprovar(cliente, solicitacao_id, cotacao["id"])

    assert resposta.status_code == 400
    assert resposta.json() == {
        "detail": "A cotação está vencida."
    }


def test_nao_aprovar_cotacao_inexistente(cliente_autenticado):
    cliente = cliente_autenticado
    solicitacao_id, cabo, conector = criar_solicitacao_com_dois_itens(cliente)
    fornecedor_id = criar_fornecedor(cliente, "Fornecedor A")

    registrar_cotacao(
        cliente, solicitacao_id, fornecedor_id,
        {cabo: 2, conector: 1}
    )

    resposta = aprovar(cliente, solicitacao_id, 9999)

    assert resposta.status_code == 404


def test_nao_aprovar_solicitacao_sem_cotacao(cliente_autenticado):
    solicitacao_id, _, _ = criar_solicitacao_com_dois_itens(
        cliente_autenticado
    )

    resposta = aprovar(cliente_autenticado, solicitacao_id, 1)

    assert resposta.status_code == 409


def test_nao_aprovar_duas_vezes(cliente_autenticado):
    solicitacao_id, cotacao = solicitacao_aprovada(cliente_autenticado)

    resposta = aprovar(cliente_autenticado, solicitacao_id, cotacao["id"])

    assert resposta.status_code == 409


def test_aprovada_bloqueia_cotacoes(cliente_autenticado):
    solicitacao_id, cotacao = solicitacao_aprovada(cliente_autenticado)

    resposta = cliente_autenticado.delete(
        f"/solicitacoes-compra/{solicitacao_id}/cotacoes/{cotacao['id']}"
    )

    assert resposta.status_code == 409


def test_aprovada_pode_ser_cancelada(cliente_autenticado):
    solicitacao_id, _ = solicitacao_aprovada(cliente_autenticado)

    resposta = cliente_autenticado.patch(
        f"/solicitacoes-compra/{solicitacao_id}/cancelar"
    )

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "CANCELADA"


def test_reprovar_solicitacao(cliente_autenticado):
    cliente = cliente_autenticado
    solicitacao_id, cabo, conector = criar_solicitacao_com_dois_itens(cliente)
    fornecedor_id = criar_fornecedor(cliente, "Fornecedor A")

    registrar_cotacao(
        cliente, solicitacao_id, fornecedor_id,
        {cabo: 2, conector: 1}
    )

    resposta = cliente.patch(
        f"/solicitacoes-compra/{solicitacao_id}/reprovar",
        json={
            "justificativa": "Valores acima do orçamento"
        }
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["status"] == "REPROVADA"
    assert dados["cotacao_aprovada_id"] is None
    assert dados["justificativa_decisao"] == "Valores acima do orçamento"

    cancelamento = cliente.patch(
        f"/solicitacoes-compra/{solicitacao_id}/cancelar"
    )

    assert cancelamento.status_code == 409


def test_reprovar_exige_justificativa(cliente_autenticado):
    solicitacao_id, _, _ = criar_solicitacao_com_dois_itens(
        cliente_autenticado
    )

    resposta = cliente_autenticado.patch(
        f"/solicitacoes-compra/{solicitacao_id}/reprovar",
        json={}
    )

    assert resposta.status_code == 422


def test_aprovar_solicitacao_inexistente(cliente_autenticado):
    resposta = aprovar(cliente_autenticado, 9999, 1)

    assert resposta.status_code == 404
