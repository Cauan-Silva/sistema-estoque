from jose import jwt

from backend.autenticacao import (
    ALGORITMO,
    CHAVE_SECRETA,
    criar_token_acesso,
    validar_token_acesso,
)


def test_criar_token_acesso():
    token = criar_token_acesso(
        usuario_id=1,
        email="usuario@teste.com"
    )

    assert isinstance(token, str)
    assert token != ""


def test_validar_token_acesso():
    token = criar_token_acesso(
        usuario_id=10,
        email="usuario@teste.com"
    )

    dados = validar_token_acesso(token)

    assert dados is not None
    assert dados["usuario_id"] == 10
    assert dados["email"] == "usuario@teste.com"


def test_token_contem_expiracao():
    token = criar_token_acesso(
        usuario_id=1,
        email="usuario@teste.com"
    )

    dados = jwt.decode(
        token,
        CHAVE_SECRETA,
        algorithms=[ALGORITMO]
    )

    assert "exp" in dados


def test_token_invalido():
    dados = validar_token_acesso(
        "token.invalido.teste"
    )

    assert dados is None