from backend.orcamentos import leitura
from backend.tests.apoio_compras import criar_fornecedor, criar_produto, novo_cliente

XML_NFE = b"""<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"><NFe><infNFe>
<ide><nNF>2162448</nNF><dhEmi>2026-09-30T21:47:17-03:00</dhEmi></ide>
<emit><CNPJ>08606542000114</CNPJ><xNome>TNTINFO COMERCIO</xNome></emit>
<det nItem="1"><prod><cProd>3455</cProd><xProd>Kit Teclado E Mouse Logitech Mk200</xProd>
<uCom>UNID</uCom><qCom>3.0000</qCom><vUnCom>99.97</vUnCom><vProd>299.91</vProd></prod>
<imposto><IPI><IPITrib><vIPI>30.77</vIPI></IPITrib></IPI></imposto></det>
<total><ICMSTot><vFrete>15.00</vFrete></ICMSTot></total>
</infNFe></NFe></nfeProc>"""

PDF_FALSO = b"%PDF-1.4 orcamento"


def ler(cliente, conteudo, nome):
    return cliente.post("/orcamentos/ler", files={"arquivo": (nome, conteudo, "application/octet-stream")})


def resposta_ia(**dados):
    return {"content": [{"type": "tool_use", "name": "registrar_orcamento", "input": dados}]}


def test_ler_xml_de_nfe_sem_ia(cliente_autenticado, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    produto = criar_produto(cliente_autenticado, "Kit teclado e mouse Logitech MK200")
    fornecedor = cliente_autenticado.post(
        "/fornecedores", json={"nome": "TNT Info", "cpf_cnpj": "08.606.542/0001-14"}
    ).json()

    resposta = ler(cliente_autenticado, XML_NFE, "nota.xml")

    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["origem"] == "xml"
    assert dados["fornecedor_sugerido"] == {"id": fornecedor["id"], "nome": "TNT Info"}
    assert dados["frete"] == 15
    item = dados["itens"][0]
    assert item["quantidade"] == 3
    assert item["preco_unitario"] == round((299.91 + 30.77) / 3, 4)
    assert item["produto_sugerido"]["id"] == produto
    assert "nota fiscal" in dados["avisos"][0]


def test_pdf_sem_chave_explica_configuracao(cliente_autenticado, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    resposta = ler(cliente_autenticado, PDF_FALSO, "orcamento.pdf")

    assert resposta.status_code == 503
    assert "ANTHROPIC_API_KEY" in resposta.json()["detail"]
    assert cliente_autenticado.get("/orcamentos/configuracao").json() == {"leitura_por_ia": False}


def test_pdf_lido_pela_ia(cliente_autenticado, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "chave-teste")
    enviados = []

    def chamar(corpo):
        enviados.append(corpo)
        return resposta_ia(
            tipo_documento="orcamento",
            fornecedor_nome="FIBRATECH TELECOM IMPORTAÇÃO LTDA",
            fornecedor_cnpj=None,
            data_emissao="2026-10-05",
            prazo_entrega_dias=10,
            frete=0,
            condicao_pagamento="28/56/84 dias",
            itens=[
                {"codigo": "301", "descricao": "Adaptador (acoplador) APC/VERDE", "unidade": "UN",
                 "quantidade": 1000, "preco_unitario": 0.439, "valor_total": 439},
                {"descricao": "linha sem quantidade", "quantidade": 0, "preco_unitario": 1, "valor_total": 0},
            ],
        )

    monkeypatch.setattr(leitura, "chamar_api", chamar)
    criar_fornecedor(cliente_autenticado, "Fibratech Telecom Importação Ltda")
    adaptador = criar_produto(cliente_autenticado, "Adaptador APC verde")

    resposta = ler(cliente_autenticado, PDF_FALSO, "orcamento.pdf")

    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["origem"] == "ia"
    assert dados["fornecedor_sugerido"]["nome"] == "Fibratech Telecom Importação Ltda"
    assert len(dados["itens"]) == 1
    assert dados["itens"][0]["preco_unitario"] == 0.439
    assert dados["itens"][0]["produto_sugerido"]["id"] == adaptador
    assert enviados[0]["messages"][0]["content"][0]["type"] == "document"
    assert enviados[0]["tool_choice"]["name"] == "registrar_orcamento"


def test_formato_nao_suportado(cliente_autenticado):
    resposta = ler(cliente_autenticado, b"PK\x03\x04 planilha", "orcamento.docx")

    assert resposta.status_code == 400


def test_consulta_nao_le_orcamentos(cliente_autenticado):
    resposta = ler(novo_cliente("CONSULTA"), XML_NFE, "nota.xml")

    assert resposta.status_code == 403


def test_criar_solicitacao_com_cotacoes_e_lembrar_referencia(cliente_autenticado, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cabo = criar_produto(cliente_autenticado, "Cabo drop")
    alca = criar_produto(cliente_autenticado, "Alça")
    fornecedor_a = criar_fornecedor(cliente_autenticado, "Fornecedor A")
    fornecedor_b = criar_fornecedor(cliente_autenticado, "Fornecedor B")

    resposta = cliente_autenticado.post("/orcamentos/solicitacao", json={
        "observacao": "Obra do bloco B",
        "itens": [{"produto_id": cabo, "quantidade": 1000}, {"produto_id": alca, "quantidade": 600}],
        "orcamentos": [
            {
                "fornecedor_id": fornecedor_a, "frete": 0, "prazo_entrega_dias": 30,
                "itens": [
                    {"produto_id": cabo, "preco_unitario": 2.59, "codigo_fornecedor": "300202013",
                     "descricao_fornecedor": "ALCA APF FO 5,71"},
                    {"produto_id": alca, "preco_unitario": 4.0435},
                ],
            },
            {
                "fornecedor_id": fornecedor_b, "frete": 50, "prazo_entrega_dias": 10,
                "itens": [{"produto_id": cabo, "preco_unitario": 2.40}],
            },
        ],
    })

    assert resposta.status_code == 201
    solicitacao = resposta.json()
    assert solicitacao["status"] == "EM_COTACAO"
    assert solicitacao["observacao"] == "Obra do bloco B"

    cotacoes = cliente_autenticado.get(f"/solicitacoes-compra/{solicitacao['id']}/cotacoes").json()
    assert len(cotacoes) == 2
    precos = {i["produto_id"]: i["preco_unitario"] for c in cotacoes for i in c["itens"] if c["fornecedor_id"] == fornecedor_a}
    assert precos[alca] == 4.0435
    assert next(c for c in cotacoes if c["fornecedor_id"] == fornecedor_a)["valor_itens"] == round(2.59 * 1000 + 4.0435 * 600, 2)

    # A associação fica lembrada para o próximo orçamento do mesmo fornecedor
    from backend.repositorio_orcamento import buscar_referencias
    referencias = buscar_referencias(fornecedor_a)
    assert referencias["codigo:300202013"] == cabo


def test_criar_solicitacao_valida_conjunto(cliente_autenticado):
    cabo = criar_produto(cliente_autenticado, "Cabo drop")
    fornecedor = criar_fornecedor(cliente_autenticado, "Fornecedor A")
    orcamento = {"fornecedor_id": fornecedor, "prazo_entrega_dias": 5, "itens": [{"produto_id": cabo, "preco_unitario": 1}]}

    repetido = cliente_autenticado.post("/orcamentos/solicitacao", json={
        "itens": [{"produto_id": cabo, "quantidade": 1}],
        "orcamentos": [orcamento, orcamento],
    })
    assert repetido.status_code == 422

    fora = cliente_autenticado.post("/orcamentos/solicitacao", json={
        "itens": [{"produto_id": cabo, "quantidade": 1}],
        "orcamentos": [{**orcamento, "itens": [{"produto_id": 9999, "preco_unitario": 1}]}],
    })
    assert fora.status_code == 422

    inexistente = cliente_autenticado.post("/orcamentos/solicitacao", json={
        "itens": [{"produto_id": 9999, "quantidade": 1}],
        "orcamentos": [],
    })
    assert inexistente.status_code == 404

    assert cliente_autenticado.get("/solicitacoes-compra").json() == []
