import os

import pytest
from fastapi.testclient import TestClient


os.environ["DB_NAME"] = "sistema_estoque_test"

from backend.database import conectar, criar_tabela
from backend.main import app


@pytest.fixture(scope="session", autouse=True)
def preparar_banco_testes():
    criar_tabela()

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
            movimentacoes,
            produtos,
            categorias
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