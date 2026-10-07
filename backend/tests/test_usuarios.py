import bcrypt

from backend.repositorio_usuario import (
    buscar_usuario_por_email,
    cadastrar_usuario,
    gerar_hash_senha,
    verificar_senha,
)


def test_gerar_hash_senha():
    senha = "senha123"

    senha_hash = gerar_hash_senha(senha)

    assert senha_hash != senha
    assert bcrypt.checkpw(
        senha.encode("utf-8"),
        senha_hash.encode("utf-8")
    )


def test_verificar_senha_correta():
    senha = "senha123"
    senha_hash = gerar_hash_senha(senha)

    resultado = verificar_senha(
        senha,
        senha_hash
    )

    assert resultado is True


def test_verificar_senha_incorreta():
    senha_hash = gerar_hash_senha("senha123")

    resultado = verificar_senha(
        "senha_errada",
        senha_hash
    )

    assert resultado is False


def test_cadastrar_usuario():
    usuario, erro = cadastrar_usuario(
        nome="Usuario Teste",
        email="usuario@teste.com",
        senha="senha123"
    )

    assert erro is None
    assert usuario is not None
    assert usuario[1] == "Usuario Teste"
    assert usuario[2] == "usuario@teste.com"
    assert usuario[3] is True


def test_buscar_usuario_por_email():
    cadastrar_usuario(
        nome="Usuario Busca",
        email="busca@teste.com",
        senha="senha123"
    )

    usuario = buscar_usuario_por_email("busca@teste.com")

    assert usuario is not None
    assert usuario[1] == "Usuario Busca"
    assert usuario[2] == "busca@teste.com"

    senha_hash = usuario[3]

    assert bcrypt.checkpw(
        "senha123".encode("utf-8"),
        senha_hash.encode("utf-8")
    )


def test_email_convertido_para_minusculo():
    usuario, erro = cadastrar_usuario(
        nome="Usuario Email",
        email="EMAIL@TESTE.COM",
        senha="senha123"
    )

    assert erro is None
    assert usuario[2] == "email@teste.com"


def test_email_duplicado():
    cadastrar_usuario(
        nome="Primeiro Usuario",
        email="duplicado@teste.com",
        senha="senha123"
    )

    usuario, erro = cadastrar_usuario(
        nome="Segundo Usuario",
        email="duplicado@teste.com",
        senha="outrasenha123"
    )

    assert usuario is None
    assert erro == "email_duplicado"


def test_api_cadastrar_usuario(client):
    resposta = client.post(
        "/usuarios",
        json={
            "nome": "Usuario API",
            "email": "api@teste.com",
            "senha": "senha123"
        }
    )

    assert resposta.status_code == 201

    dados = resposta.json()

    assert dados["nome"] == "Usuario API"
    assert dados["email"] == "api@teste.com"
    assert dados["ativo"] is True
    assert "id" in dados
    assert "data_criacao" in dados


def test_api_nao_retorna_senha(client):
    resposta = client.post(
        "/usuarios",
        json={
            "nome": "Usuario Seguro",
            "email": "seguro@teste.com",
            "senha": "senha123"
        }
    )

    assert resposta.status_code == 201

    dados = resposta.json()

    assert "senha" not in dados
    assert "senha_hash" not in dados


def test_api_email_duplicado(client):
    dados = {
        "nome": "Usuario Duplicado",
        "email": "duplicado-api@teste.com",
        "senha": "senha123"
    }

    primeira_resposta = client.post(
        "/usuarios",
        json=dados
    )

    segunda_resposta = client.post(
        "/usuarios",
        json=dados
    )

    assert primeira_resposta.status_code == 201
    assert segunda_resposta.status_code == 409

    assert segunda_resposta.json() == {
        "detail": "E-mail já cadastrado."
    }


def test_api_email_invalido(client):
    resposta = client.post(
        "/usuarios",
        json={
            "nome": "Usuario Email Invalido",
            "email": "email-invalido",
            "senha": "senha123"
        }
    )

    assert resposta.status_code == 422


def test_api_senha_curta(client):
    resposta = client.post(
        "/usuarios",
        json={
            "nome": "Usuario Senha Curta",
            "email": "senha@teste.com",
            "senha": "123"
        }
    )

    assert resposta.status_code == 422