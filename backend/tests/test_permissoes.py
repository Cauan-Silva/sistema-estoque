import pytest

from backend.tests.apoio_compras import (
    compra_registrada,
    criar_produto,
    novo_cliente,
)


def test_primeiro_usuario_e_administrador_e_os_demais_consulta(client):
    primeiro = client.post(
        "/usuarios",
        json={"nome": "Primeiro", "email": "primeiro@teste.com", "senha": "senha123"}
    )
    segundo = client.post(
        "/usuarios",
        json={"nome": "Segundo", "email": "segundo@teste.com", "senha": "senha123"}
    )

    assert primeiro.json()["perfil"] == "ADMINISTRADOR"
    assert segundo.json()["perfil"] == "CONSULTA"


def test_usuario_atual_mostra_perfil_e_permissoes(cliente_autenticado):
    dados = cliente_autenticado.get("/usuarios/me").json()

    assert dados["perfil"] == "ADMINISTRADOR"
    assert "usuarios.gerenciar" in dados["permissoes"]

    consulta = novo_cliente("CONSULTA").get("/usuarios/me").json()

    assert consulta["perfil"] == "CONSULTA"
    assert consulta["permissoes"] == []


@pytest.mark.parametrize(
    "perfil, pode",
    [
        ("ADMINISTRADOR", True),
        ("ALMOXARIFE", True),
        ("COMPRADOR", False),
        ("APROVADOR", False),
        ("CONSULTA", False),
    ],
)
def test_permissao_para_cadastrar_categoria(cliente_autenticado, perfil, pode):
    cliente = cliente_autenticado if perfil == "ADMINISTRADOR" else novo_cliente(perfil)

    resposta = cliente.post("/categorias", json={"nome": f"Categoria {perfil}"})

    assert resposta.status_code == (201 if pode else 403)


def test_consulta_pode_ler_mas_nao_alterar(cliente_autenticado):
    criar_produto(cliente_autenticado, "Produto Leitura")
    consulta = novo_cliente("CONSULTA")

    assert consulta.get("/produtos").status_code == 200
    assert consulta.get("/fornecedores").status_code == 200
    assert consulta.get("/relatorios/compras").status_code == 200

    tentativas = [
        consulta.post("/fornecedores", json={"nome": "Não pode"}),
        consulta.post("/solicitacoes-compra", json={"itens": [{"produto_id": 1, "quantidade": 1}]}),
        consulta.post("/movimentacoes", json={"produto_id": 1, "tipo": "ENTRADA", "quantidade": 1}),
    ]

    for resposta in tentativas:
        assert resposta.status_code == 403
        assert resposta.json() == {"detail": "Seu perfil não tem permissão para esta ação."}


def test_comprador_nao_registra_recebimento(cliente_autenticado):
    solicitacao_id, _ = compra_registrada(cliente_autenticado)

    comprador = novo_cliente("COMPRADOR")
    almoxarife = novo_cliente("ALMOXARIFE")

    url = f"/solicitacoes-compra/{solicitacao_id}/compra/recebimentos"

    assert comprador.post(url, json={}).status_code == 403
    assert almoxarife.post(url, json={}).status_code == 201


def test_administrador_gerencia_usuarios(cliente_autenticado):
    novo_cliente("CONSULTA", "Pessoa Nova")

    usuarios = cliente_autenticado.get("/usuarios").json()
    pessoa = next(u for u in usuarios if u["nome"] == "Pessoa Nova")

    assert pessoa["perfil"] == "CONSULTA"

    alterado = cliente_autenticado.patch(
        f"/usuarios/{pessoa['id']}",
        json={"perfil": "COMPRADOR"}
    )

    assert alterado.status_code == 200
    assert alterado.json()["perfil"] == "COMPRADOR"
    assert alterado.json()["ativo"] is True

    desativado = cliente_autenticado.patch(
        f"/usuarios/{pessoa['id']}",
        json={"ativo": False}
    )

    assert desativado.json()["ativo"] is False
    assert desativado.json()["perfil"] == "COMPRADOR"


def test_somente_administrador_gerencia_usuarios(cliente_autenticado):
    comprador = novo_cliente("COMPRADOR")

    assert comprador.get("/usuarios").status_code == 403
    assert comprador.patch("/usuarios/1", json={"perfil": "ADMINISTRADOR"}).status_code == 403


def test_administrador_nao_remove_o_proprio_acesso(cliente_autenticado):
    eu = cliente_autenticado.get("/usuarios/me").json()

    rebaixar = cliente_autenticado.patch(f"/usuarios/{eu['id']}", json={"perfil": "CONSULTA"})
    desativar = cliente_autenticado.patch(f"/usuarios/{eu['id']}", json={"ativo": False})

    assert rebaixar.status_code == 409
    assert desativar.status_code == 409


def test_alterar_usuario_inexistente(cliente_autenticado):
    resposta = cliente_autenticado.patch("/usuarios/999999", json={"perfil": "COMPRADOR"})

    assert resposta.status_code == 404


def test_perfil_invalido(cliente_autenticado):
    eu = cliente_autenticado.get("/usuarios/me").json()

    resposta = cliente_autenticado.patch(f"/usuarios/{eu['id']}", json={"perfil": "DONO"})

    assert resposta.status_code == 422
