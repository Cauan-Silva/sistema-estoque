from backend.repositorio_fornecedor import (
    buscar_fornecedor,
    cadastrar_fornecedor,
    listar_fornecedores,
)


def test_cadastrar_fornecedor():
    fornecedor = cadastrar_fornecedor(
        nome="Fornecedor Teste",
        cpf_cnpj="12345678000199",
        contato="João",
        telefone="48999999999",
        email="contato@fornecedor.com",
        site="https://fornecedor.com"
    )

    assert fornecedor is not None
    assert fornecedor[1] == "Fornecedor Teste"
    assert fornecedor[2] == "12345678000199"
    assert fornecedor[3] == "João"
    assert fornecedor[4] == "48999999999"
    assert fornecedor[5] == "contato@fornecedor.com"
    assert fornecedor[6] == "https://fornecedor.com"
    assert fornecedor[7] is True


def test_buscar_fornecedor():
    fornecedor_cadastrado = cadastrar_fornecedor(
        nome="Fornecedor Busca",
        email="busca@fornecedor.com"
    )

    assert fornecedor_cadastrado is not None

    fornecedor = buscar_fornecedor(
        fornecedor_cadastrado[0]
    )

    assert fornecedor is not None
    assert fornecedor[0] == fornecedor_cadastrado[0]
    assert fornecedor[1] == "Fornecedor Busca"
    assert fornecedor[5] == "busca@fornecedor.com"


def test_buscar_fornecedor_inexistente():
    fornecedor = buscar_fornecedor(999999)

    assert fornecedor is None


def test_listar_fornecedores():
    cadastrar_fornecedor(
        nome="Fornecedor B"
    )

    cadastrar_fornecedor(
        nome="Fornecedor A"
    )

    fornecedores = listar_fornecedores()

    assert len(fornecedores) == 2
    assert fornecedores[0][1] == "Fornecedor A"
    assert fornecedores[1][1] == "Fornecedor B"