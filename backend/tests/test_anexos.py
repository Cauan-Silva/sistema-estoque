from backend.tests.apoio_compras import criar_fornecedor, criar_solicitacao_com_dois_itens, novo_cliente

PDF = b"%PDF-1.4 nota fiscal de teste"


def anexar(cliente, solicitacao_id, nome="nota.pdf", conteudo=PDF, **dados):
    return cliente.post(
        f"/solicitacoes-compra/{solicitacao_id}/anexos",
        files={"arquivo": (nome, conteudo, "application/octet-stream")},
        data={k: str(v) for k, v in dados.items()},
    )


def test_anexar_listar_baixar_e_excluir(cliente_autenticado):
    solicitacao_id, _, _ = criar_solicitacao_com_dois_itens(cliente_autenticado)
    fornecedor = criar_fornecedor(cliente_autenticado, "Fornecedor A")

    resposta = anexar(
        cliente_autenticado, solicitacao_id, nome="NF 123 São José.pdf",
        tipo="NOTA_FISCAL", descricao="NF da primeira entrega", fornecedor_id=fornecedor,
    )

    assert resposta.status_code == 201
    anexo = resposta.json()
    assert anexo["tipo"] == "NOTA_FISCAL"
    assert anexo["tamanho"] == len(PDF)
    assert anexo["tipo_conteudo"] == "application/pdf"
    assert anexo["fornecedor"] == "Fornecedor A"
    assert anexo["usuario"] == "Usuario Testes"

    lista = cliente_autenticado.get(f"/solicitacoes-compra/{solicitacao_id}/anexos").json()
    assert [a["id"] for a in lista] == [anexo["id"]]
    assert "conteudo" not in lista[0]

    arquivo = cliente_autenticado.get(f"/solicitacoes-compra/{solicitacao_id}/anexos/{anexo['id']}")
    assert arquivo.status_code == 200
    assert arquivo.content == PDF
    assert arquivo.headers["content-type"] == "application/pdf"
    assert "inline" in arquivo.headers["content-disposition"]
    assert "S%C3%A3o" in arquivo.headers["content-disposition"]
    assert arquivo.headers["x-content-type-options"] == "nosniff"

    assert cliente_autenticado.delete(f"/solicitacoes-compra/{solicitacao_id}/anexos/{anexo['id']}").status_code == 204
    assert cliente_autenticado.get(f"/solicitacoes-compra/{solicitacao_id}/anexos").json() == []


def test_regras_do_arquivo(cliente_autenticado):
    solicitacao_id, _, _ = criar_solicitacao_com_dois_itens(cliente_autenticado)

    assert anexar(cliente_autenticado, solicitacao_id, nome="pagina.html", conteudo=b"<script>").status_code == 400
    assert anexar(cliente_autenticado, solicitacao_id, nome="imagem.svg", conteudo=b"<svg/>").status_code == 400
    assert anexar(cliente_autenticado, solicitacao_id, nome="vazio.pdf", conteudo=b"").status_code == 400
    assert anexar(cliente_autenticado, solicitacao_id, conteudo=b"x" * (10 * 1024 * 1024 + 1)).status_code == 413
    assert anexar(cliente_autenticado, solicitacao_id, tipo="QUALQUER").status_code == 422
    assert anexar(cliente_autenticado, 9999).status_code == 404

    planilha = anexar(cliente_autenticado, solicitacao_id, nome="proposta.xlsx", conteudo=b"PK\x03\x04", tipo="PROPOSTA")
    assert planilha.status_code == 201
    baixada = cliente_autenticado.get(f"/solicitacoes-compra/{solicitacao_id}/anexos/{planilha.json()['id']}")
    assert "attachment" in baixada.headers["content-disposition"]


def test_permissoes(cliente_autenticado):
    solicitacao_id, _, _ = criar_solicitacao_com_dois_itens(cliente_autenticado)

    assert anexar(novo_cliente("CONSULTA"), solicitacao_id).status_code == 403

    almoxarife = novo_cliente("ALMOXARIFE")
    do_almoxarife = anexar(almoxarife, solicitacao_id, tipo="NOTA_FISCAL")
    assert do_almoxarife.status_code == 201

    outro = novo_cliente("COMPRADOR")
    anexo_id = do_almoxarife.json()["id"]
    assert outro.delete(f"/solicitacoes-compra/{solicitacao_id}/anexos/{anexo_id}").status_code == 403
    assert novo_cliente("CONSULTA").get(f"/solicitacoes-compra/{solicitacao_id}/anexos/{anexo_id}").status_code == 200
    assert cliente_autenticado.delete(f"/solicitacoes-compra/{solicitacao_id}/anexos/{anexo_id}").status_code == 204
