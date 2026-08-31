from typing import Literal

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    status
)

from backend.repositorio_movimentacao import (
    buscar_movimentacao_por_id,
    listar_movimentacoes,
    registrar_movimentacao
)

from backend.schemas.movimentacao import (
    MovimentacaoCriar,
    MovimentacaoResposta
)


router = APIRouter(
    prefix="/movimentacoes",
    tags=["Movimentações"]
)


@router.get(
    "",
    response_model=list[MovimentacaoResposta]
)
def obter_movimentacoes(
    produto_id: int | None = Query(
        default=None,
        gt=0
    ),
    tipo: Literal[
        "ENTRADA",
        "SAIDA"
    ] | None = Query(
        default=None
    )
):
    return listar_movimentacoes(
        produto_id=produto_id,
        tipo=tipo
    )


@router.get(
    "/{id_movimentacao}",
    response_model=MovimentacaoResposta
)
def obter_movimentacao(
    id_movimentacao: int
):
    movimentacao = buscar_movimentacao_por_id(
        id_movimentacao
    )

    if movimentacao is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movimentação não encontrada."
        )

    return movimentacao


@router.post(
    "",
    response_model=MovimentacaoResposta,
    status_code=status.HTTP_201_CREATED
)
def criar_movimentacao(
    dados: MovimentacaoCriar
):
    movimentacao, erro = registrar_movimentacao(
        dados.produto_id,
        dados.tipo,
        dados.quantidade
    )

    if erro == "produto_nao_encontrado":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado."
        )

    if erro == "estoque_insuficiente":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Estoque insuficiente para "
                "realizar a saída."
            )
        )

    if erro == "tipo_invalido":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de movimentação inválido."
        )

    if movimentacao is None:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Não foi possível registrar "
                "a movimentação."
            )
        )

    return movimentacao