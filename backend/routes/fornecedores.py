from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from backend.autenticacao import obter_usuario_atual
from backend.repositorio_fornecedor import (
    buscar_fornecedor,
    cadastrar_fornecedor,
    listar_fornecedores,
)
from backend.schemas.fornecedor import (
    FornecedorCriacao,
    FornecedorResposta,
)


router = APIRouter(
    prefix="/fornecedores",
    tags=["Fornecedores"],
    dependencies=[
        Depends(obter_usuario_atual)
    ]
)


def fornecedor_para_resposta(fornecedor):
    return {
        "id": fornecedor[0],
        "nome": fornecedor[1],
        "cpf_cnpj": fornecedor[2],
        "contato": fornecedor[3],
        "telefone": fornecedor[4],
        "email": fornecedor[5],
        "site": fornecedor[6],
        "ativo": fornecedor[7],
        "data_criacao": fornecedor[8]
    }


@router.post(
    "",
    response_model=FornecedorResposta,
    status_code=status.HTTP_201_CREATED
)
def criar_fornecedor(
    fornecedor: FornecedorCriacao
):
    fornecedor_cadastrado = cadastrar_fornecedor(
        nome=fornecedor.nome,
        cpf_cnpj=fornecedor.cpf_cnpj,
        contato=fornecedor.contato,
        telefone=fornecedor.telefone,
        email=fornecedor.email,
        site=fornecedor.site
    )

    if fornecedor_cadastrado is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível cadastrar o fornecedor."
        )

    return fornecedor_para_resposta(
        fornecedor_cadastrado
    )


@router.get(
    "",
    response_model=list[FornecedorResposta]
)
def listar():
    fornecedores = listar_fornecedores()

    return [
        fornecedor_para_resposta(fornecedor)
        for fornecedor in fornecedores
    ]


@router.get(
    "/{fornecedor_id}",
    response_model=FornecedorResposta
)
def buscar(fornecedor_id: int):
    fornecedor = buscar_fornecedor(
        fornecedor_id
    )

    if fornecedor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fornecedor não encontrado."
        )

    return fornecedor_para_resposta(fornecedor)