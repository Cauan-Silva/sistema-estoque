import os

import pytest
from fastapi.testclient import TestClient


os.environ["DB_NAME"] = "sistema_estoque_test"

from backend.database import aplicar_migracoes, conectar
from backend.main import app


@pytest.fixture(scope="session", autouse=True)
def preparar_banco_testes():
    aplicar_migracoes()

    yield


@pytest.fixture(autouse=True)
def limpar_banco():
    conexao = conectar()

    if conexao is None:
        raise RuntimeError(
            "Não foi possível conectar ao banco de testes."
        )

    cursor = conexao.cursor()

    cursor.execute(
        """
        TRUNCATE TABLE
            auditoria,
            itens_recebimento,
            recebimentos,
            itens_compra,
            compras,
            itens_cotacao,
            cotacoes,
            itens_solicitacao_compra,
            solicitacoes_compra,
            movimentacoes,
            produtos,
            categorias,
            usuarios,
            fornecedores
        RESTART IDENTITY CASCADE;
        """
    )

    conexao.commit()

    cursor.close()
    conexao.close()

    yield


@pytest.fixture()
def client():
    with TestClient(app) as cliente:
        yield cliente

@pytest.fixture()
def cliente_autenticado():
    from backend.autenticacao import criar_token_acesso
    from backend.repositorio_usuario import cadastrar_usuario

    usuario, erro = cadastrar_usuario(
        nome="Usuario Testes",
        email="usuario.testes@teste.com",
        senha="senha123"
    )

    assert erro is None
    assert usuario is not None

    token = criar_token_acesso(
        usuario_id=usuario[0],
        email=usuario[2]
    )

    with TestClient(
        app,
        headers={
            "Authorization": f"Bearer {token}"
        }
    ) as cliente:
        yield cliente
