import uuid

from fastapi.testclient import TestClient

from backend.autenticacao import criar_token_acesso
from backend.database import conectar
from backend.main import app
from backend.repositorio_usuario import cadastrar_usuario


VALIDADE_FUTURA = "2099-12-31"
VALIDADE_VENCIDA = "2020-01-01"


def criar_produto(cliente, nome):
    categoria = cliente.post(
        "/categorias",
        json={
            "nome": f"Categoria {nome}"
        }
    )

    assert categoria.status_code == 201

    produto = cliente.post(
        "/produtos",
        json={
            "nome": nome,
            "categoria_id": categoria.json()["id"],
            "quantidade": 0,
            "preco": 10
        }
    )

    assert produto.status_code == 201

    return produto.json()["id"]


def criar_fornecedor(cliente, nome):
    resposta = cliente.post(
        "/fornecedores",
        json={
            "nome": nome
        }
    )

    assert resposta.status_code == 201

    return resposta.json()["id"]


def criar_solicitacao_com_dois_itens(cliente):
    produto_a = criar_produto(cliente, "Cabo")
    produto_b = criar_produto(cliente, "Conector")

    resposta = cliente.post(
        "/solicitacoes-compra",
        json={
            "itens": [
                {"produto_id": produto_a, "quantidade": 10},
                {"produto_id": produto_b, "quantidade": 4}
            ]
        }
    )

    assert resposta.status_code == 201

    return resposta.json()["id"], produto_a, produto_b


def registrar_cotacao(
    cliente,
    solicitacao_id,
    fornecedor_id,
    precos,
    frete=0,
    prazo=5,
    validade=VALIDADE_FUTURA
):
    resposta = cliente.post(
        f"/solicitacoes-compra/{solicitacao_id}/cotacoes",
        json={
            "fornecedor_id": fornecedor_id,
            "frete": frete,
            "prazo_entrega_dias": prazo,
            "validade": validade,
            "itens": [
                {"produto_id": produto_id, "preco_unitario": preco}
                for produto_id, preco in precos.items()
            ]
        }
    )

    assert resposta.status_code == 201

    return resposta.json()


def solicitacao_aprovada(cliente):
    solicitacao_id, produto_a, produto_b = (
        criar_solicitacao_com_dois_itens(cliente)
    )
    fornecedor_id = criar_fornecedor(cliente, "Fornecedor Aprovado")

    cotacao = registrar_cotacao(
        cliente,
        solicitacao_id,
        fornecedor_id,
        {produto_a: 2.5, produto_b: 1.25},
        frete=12,
        prazo=10
    )

    aprovacao = novo_cliente("APROVADOR").patch(
        f"/solicitacoes-compra/{solicitacao_id}/aprovar",
        json={
            "cotacao_id": cotacao["id"]
        }
    )

    assert aprovacao.status_code == 200

    return solicitacao_id, cotacao


def compra_registrada(cliente, data_compra="2026-10-01", previsao=None):
    solicitacao_id, cotacao = solicitacao_aprovada(cliente)

    corpo = {"data_compra": data_compra}

    if previsao:
        corpo["previsao_entrega"] = previsao

    resposta = cliente.post(
        f"/solicitacoes-compra/{solicitacao_id}/compra",
        json=corpo
    )

    assert resposta.status_code == 201

    return solicitacao_id, resposta.json()


def novo_cliente(perfil, nome=None):
    """Cria um usuário com o perfil informado e devolve um cliente autenticado."""
    sufixo = uuid.uuid4().hex[:8]

    usuario, erro = cadastrar_usuario(
        nome=nome or f"Usuario {perfil.title()}",
        email=f"{perfil.lower()}.{sufixo}@teste.com",
        senha="senha123"
    )

    assert erro is None

    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute(
        "UPDATE usuarios SET perfil = %s WHERE id = %s;",
        (perfil, usuario[0])
    )
    conexao.commit()
    cursor.close()
    conexao.close()

    token = criar_token_acesso(usuario_id=usuario[0], email=usuario[2])

    return TestClient(app, headers={"Authorization": f"Bearer {token}"})
