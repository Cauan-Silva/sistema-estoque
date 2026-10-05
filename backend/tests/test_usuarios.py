import bcrypt

from backend.repositorio_usuario import (
    buscar_usuario_por_email,
    cadastrar_usuario,
    gerar_hash_senha,
)


def test_gerar_hash_senha():
    senha = "senha123"

    senha_hash = gerar_hash_senha(senha)

    assert senha_hash != senha
    assert bcrypt.checkpw(
        senha.encode("utf-8"),
        senha_hash.encode("utf-8")
    )


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