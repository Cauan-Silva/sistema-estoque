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