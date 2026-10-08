from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from backend.autenticacao import obter_usuario_atual
from backend.permissoes import exigir
from backend.repositorio_fornecedor import (
    alterar_status_fornecedor,
    atualizar_fornecedor,
    buscar_fornecedor,
    cadastrar_fornecedor,
    listar_fornecedores,
)
from backend.schemas.fornecedor import (
    FornecedorAtualizacao,
    FornecedorCriacao,
    FornecedorResposta,
    FornecedorStatus,
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
    dependencies=[exigir("fornecedores.editar")],
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
def listar(
    ativo: bool | None = Query(default=None)
):
    fornecedores = listar_fornecedores(ativo=ativo)

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


@router.put(
    "/{fornecedor_id}",
    dependencies=[exigir("fornecedores.editar")],
    response_model=FornecedorResposta
)
def editar(
    fornecedor_id: int,
    fornecedor: FornecedorAtualizacao
):
    if buscar_fornecedor(fornecedor_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fornecedor não encontrado."
        )

    fornecedor_atualizado = atualizar_fornecedor(
        fornecedor_id=fornecedor_id,
        nome=fornecedor.nome,
        cpf_cnpj=fornecedor.cpf_cnpj,
        contato=fornecedor.contato,
        telefone=fornecedor.telefone,
        email=fornecedor.email,
        site=fornecedor.site
    )

    if fornecedor_atualizado is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível atualizar o fornecedor."
        )

    return fornecedor_para_resposta(
        fornecedor_atualizado
    )


@router.patch(
    "/{fornecedor_id}/status",
    dependencies=[exigir("fornecedores.editar")],
    response_model=FornecedorResposta
)
def alterar_status(
    fornecedor_id: int,
    dados: FornecedorStatus
):
    if buscar_fornecedor(fornecedor_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fornecedor não encontrado."
        )

    fornecedor = alterar_status_fornecedor(
        fornecedor_id=fornecedor_id,
        ativo=dados.ativo
    )

    if fornecedor is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível alterar o status do fornecedor."
        )

    return fornecedor_para_resposta(fornecedor)
