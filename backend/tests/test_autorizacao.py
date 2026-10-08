import pytest

from backend.autenticacao import criar_token_acesso
from backend.repositorio_usuario import cadastrar_usuario


def test_acessar_usuario_atual_com_token(client):
    usuario, erro = cadastrar_usuario(
        nome="Usuario Autorizado",
        email="autorizado@teste.com",
        senha="senha123"
    )

    assert erro is None
    assert usuario is not None

    token = criar_token_acesso(
        usuario_id=usuario[0],
        email=usuario[2]
    )

    resposta = client.get(
        "/usuarios/me",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["id"] == usuario[0]
    assert dados["nome"] == "Usuario Autorizado"
    assert dados["email"] == "autorizado@teste.com"
    assert dados["ativo"] is True

    assert "senha" not in dados
    assert "senha_hash" not in dados


def test_acessar_usuario_atual_sem_token(client):
    resposta = client.get(
        "/usuarios/me"
    )

    assert resposta.status_code == 401


def test_acessar_usuario_atual_com_token_invalido(client):
    resposta = client.get(
        "/usuarios/me",
        headers={
            "Authorization": "Bearer token.invalido.teste"
        }
    )

    assert resposta.status_code == 401

    assert resposta.json() == {
        "detail": "Token inválido ou expirado."
    }

ROTAS_PROTEGIDAS = [
    ("get", "/produtos"),
    ("get", "/produtos/1"),
    ("post", "/produtos"),
    ("put", "/produtos/1"),
    ("delete", "/produtos/1"),
    ("get", "/categorias"),
    ("get", "/categorias/1"),
    ("post", "/categorias"),
    ("put", "/categorias/1"),
    ("delete", "/categorias/1"),
    ("get", "/movimentacoes"),
    ("get", "/movimentacoes/1"),
    ("post", "/movimentacoes"),
    ("get", "/relatorios/resumo"),
    ("get", "/relatorios/maior-valor"),
    ("get", "/fornecedores"),
    ("get", "/fornecedores/1"),
    ("post", "/fornecedores"),
    ("put", "/fornecedores/1"),
    ("patch", "/fornecedores/1/status"),
    ("get", "/solicitacoes-compra"),
    ("get", "/solicitacoes-compra/1"),
    ("post", "/solicitacoes-compra"),
    ("put", "/solicitacoes-compra/1"),
    ("patch", "/solicitacoes-compra/1/cancelar"),
    ("get", "/solicitacoes-compra/1/cotacoes"),
    ("post", "/solicitacoes-compra/1/cotacoes"),
    ("get", "/solicitacoes-compra/1/cotacoes/1"),
    ("put", "/solicitacoes-compra/1/cotacoes/1"),
    ("delete", "/solicitacoes-compra/1/cotacoes/1"),
    ("get", "/solicitacoes-compra/1/cotacoes/comparacao"),
    ("patch", "/solicitacoes-compra/1/aprovar"),
    ("patch", "/solicitacoes-compra/1/reprovar"),
    ("post", "/solicitacoes-compra/1/compra"),
    ("get", "/solicitacoes-compra/1/compra"),
    ("get", "/compras"),
    ("get", "/compras/1"),
]


@pytest.mark.parametrize("metodo, rota", ROTAS_PROTEGIDAS)
def test_rota_protegida_sem_token(client, metodo, rota):
    resposta = client.request(
        metodo.upper(),
        rota
    )

    assert resposta.status_code == 401


@pytest.mark.parametrize("metodo, rota", ROTAS_PROTEGIDAS)
def test_rota_protegida_com_token_invalido(client, metodo, rota):
    resposta = client.request(
        metodo.upper(),
        rota,
        headers={
            "Authorization": "Bearer token.invalido.teste"
        }
    )

    assert resposta.status_code == 401


def test_usuario_inativo_nao_acessa_rota_protegida(client):
    from backend.database import conectar

    usuario, erro = cadastrar_usuario(
        nome="Usuario Inativo",
        email="inativo@teste.com",
        senha="senha123"
    )

    assert erro is None

    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute(
        "UPDATE usuarios SET ativo = FALSE WHERE id = %s;",
        (usuario[0],)
    )
    conexao.commit()
    cursor.close()
    conexao.close()

    token = criar_token_acesso(
        usuario_id=usuario[0],
        email=usuario[2]
    )

    resposta = client.get(
        "/produtos",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    assert resposta.status_code == 403
