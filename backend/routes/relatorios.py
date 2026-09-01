from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    status
)

from backend.repositorio_relatorio import (
    listar_produtos_maior_valor,
    obter_resumo_estoque
)

from backend.schemas.relatorio import (
    ProdutoValorEstoqueResposta,
    ResumoEstoqueResposta
)


router = APIRouter(
    prefix="/relatorios",
    tags=["Relatórios"]
)


@router.get(
    "/resumo",
    response_model=ResumoEstoqueResposta
)
def obter_resumo(
    limite_estoque: int = Query(
        default=5,
        ge=0
    )
):
    resumo = obter_resumo_estoque(
        limite_estoque=limite_estoque
    )

    if resumo is None:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Não foi possível gerar "
                "o resumo do estoque."
            )
        )

    return resumo


@router.get(
    "/maior-valor",
    response_model=list[
        ProdutoValorEstoqueResposta
    ]
)
def obter_produtos_maior_valor(
    limite: int = Query(
        default=10,
        ge=1,
        le=100
    )
):
    return listar_produtos_maior_valor(
        limite=limite
    )