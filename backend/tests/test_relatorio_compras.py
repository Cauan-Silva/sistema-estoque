from backend.tests.apoio_compras import compra_registrada


def receber(cliente, solicitacao_id, data):
    resposta = cliente.post(
        f"/solicitacoes-compra/{solicitacao_id}/compra/recebimentos",
        json={"data_recebimento": data}
    )

    assert resposta.status_code == 201


def test_relatorio_sem_compras(cliente_autenticado):
    resposta = cliente_autenticado.get("/relatorios/compras")

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["total_compras"] == 0
    assert dados["valor_total"] == 0
    assert dados["ticket_medio"] == 0
    assert dados["percentual_no_prazo"] is None
    assert dados["prazo_medio_entrega_dias"] is None
    assert dados["por_fornecedor"] == []
    assert dados["por_produto"] == []
    assert dados["por_mes"] == []


def test_relatorio_de_compras(cliente_autenticado):
    cliente = cliente_autenticado

    solicitacao_id, compra = compra_registrada(cliente, data_compra="2026-10-01")
    receber(cliente, solicitacao_id, "2026-10-08")

    dados = cliente.get(
        "/relatorios/compras?data_inicio=2026-10-01&data_fim=2026-10-31"
    ).json()

    assert dados["total_compras"] == 1
    assert dados["valor_total"] == 42.0
    assert dados["valor_itens"] == 30.0
    assert dados["frete_total"] == 12.0
    assert dados["ticket_medio"] == 42.0
    assert dados["compras_recebidas"] == 1
    assert dados["compras_pendentes"] == 0
    assert dados["entregas_no_prazo"] == 1
    assert dados["entregas_atrasadas"] == 0
    assert dados["percentual_no_prazo"] == 100.0
    assert dados["prazo_medio_entrega_dias"] == 7.0

    assert dados["por_fornecedor"] == [
        {
            "fornecedor_id": compra["fornecedor_id"],
            "fornecedor": "Fornecedor Aprovado",
            "compras": 1,
            "valor_total": 42.0,
            "entregas_no_prazo": 1,
            "entregas_atrasadas": 0
        }
    ]

    assert dados["por_mes"] == [
        {"mes": "2026-10", "compras": 1, "valor_total": 42.0}
    ]

    produtos = {p["produto"]: p for p in dados["por_produto"]}

    assert produtos["Cabo"]["quantidade"] == 10
    assert produtos["Cabo"]["valor_total"] == 25.0
    assert produtos["Cabo"]["preco_medio"] == 2.5
    assert produtos["Conector"]["valor_total"] == 5.0
    assert [p["produto"] for p in dados["por_produto"]] == ["Cabo", "Conector"]


def test_relatorio_fora_do_periodo(cliente_autenticado):
    compra_registrada(cliente_autenticado, data_compra="2026-10-01")

    dados = cliente_autenticado.get(
        "/relatorios/compras?data_inicio=2026-11-01"
    ).json()

    assert dados["total_compras"] == 0


def test_relatorio_compra_atrasada_em_aberto(cliente_autenticado):
    compra_registrada(
        cliente_autenticado,
        data_compra="2020-01-01",
        previsao="2020-01-10"
    )

    dados = cliente_autenticado.get("/relatorios/compras").json()

    assert dados["compras_pendentes"] == 1
    assert dados["atrasadas_em_aberto"] == 1


def test_relatorio_periodo_invertido(cliente_autenticado):
    resposta = cliente_autenticado.get(
        "/relatorios/compras?data_inicio=2026-10-31&data_fim=2026-10-01"
    )

    assert resposta.status_code == 400
