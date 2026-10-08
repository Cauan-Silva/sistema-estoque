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

def criar_fornecedor_api(
    cliente,
    nome="Fornecedor API",
    email="api@fornecedor.com"
):
    resposta = cliente.post(
        "/fornecedores",
        json={
            "nome": nome,
            "email": email
        }
    )

    assert resposta.status_code == 201

    return resposta.json()


def test_api_atualizar_fornecedor(cliente_autenticado):
    fornecedor = criar_fornecedor_api(cliente_autenticado)

    resposta = cliente_autenticado.put(
        f"/fornecedores/{fornecedor['id']}",
        json={
            "nome": "Fornecedor Atualizado",
            "cpf_cnpj": "98765432000111",
            "contato": "Maria",
            "telefone": "48988887777",
            "email": "novo@fornecedor.com",
            "site": "https://novo.com"
        }
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["id"] == fornecedor["id"]
    assert dados["nome"] == "Fornecedor Atualizado"
    assert dados["cpf_cnpj"] == "98765432000111"
    assert dados["contato"] == "Maria"
    assert dados["email"] == "novo@fornecedor.com"
    assert dados["ativo"] is True


def test_api_atualizar_fornecedor_inexistente(cliente_autenticado):
    resposta = cliente_autenticado.put(
        "/fornecedores/9999",
        json={
            "nome": "Fornecedor"
        }
    )

    assert resposta.status_code == 404

    assert resposta.json() == {
        "detail": "Fornecedor não encontrado."
    }


def test_api_inativar_e_reativar_fornecedor(cliente_autenticado):
    fornecedor = criar_fornecedor_api(cliente_autenticado)

    inativado = cliente_autenticado.patch(
        f"/fornecedores/{fornecedor['id']}/status",
        json={
            "ativo": False
        }
    )

    assert inativado.status_code == 200
    assert inativado.json()["ativo"] is False

    reativado = cliente_autenticado.patch(
        f"/fornecedores/{fornecedor['id']}/status",
        json={
            "ativo": True
        }
    )

    assert reativado.status_code == 200
    assert reativado.json()["ativo"] is True


def test_api_status_fornecedor_inexistente(cliente_autenticado):
    resposta = cliente_autenticado.patch(
        "/fornecedores/9999/status",
        json={
            "ativo": False
        }
    )

    assert resposta.status_code == 404


def test_api_filtrar_fornecedores_por_status(cliente_autenticado):
    ativo = criar_fornecedor_api(
        cliente_autenticado,
        nome="Fornecedor Ativo",
        email="ativo@fornecedor.com"
    )
    inativo = criar_fornecedor_api(
        cliente_autenticado,
        nome="Fornecedor Inativo",
        email="inativo@fornecedor.com"
    )

    cliente_autenticado.patch(
        f"/fornecedores/{inativo['id']}/status",
        json={
            "ativo": False
        }
    )

    ativos = cliente_autenticado.get(
        "/fornecedores?ativo=true"
    ).json()
    inativos = cliente_autenticado.get(
        "/fornecedores?ativo=false"
    ).json()
    todos = cliente_autenticado.get(
        "/fornecedores"
    ).json()

    assert [f["id"] for f in ativos] == [ativo["id"]]
    assert [f["id"] for f in inativos] == [inativo["id"]]
    assert len(todos) == 2
