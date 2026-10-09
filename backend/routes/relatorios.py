from datetime import date

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status
)

from backend.autenticacao import obter_usuario_atual
from backend.repositorio_relatorio import (
    listar_produtos_maior_valor,
    obter_resumo_estoque
)

from backend.repositorio_relatorio_compras import (
    gerar_relatorio_compras
)

from backend.schemas.relatorio import (
    ProdutoValorEstoqueResposta,
    RelatorioComprasResposta,
    ResumoEstoqueResposta
)


router = APIRouter(
    prefix="/relatorios",
    tags=["Relatórios"],
    dependencies=[
        Depends(obter_usuario_atual)
    ]
)


@router.get(
    "/resumo",
    response_model=ResumoEstoqueResposta
)
def obter_resumo(
    limite_estoque: int | None = Query(
        default=None,
        ge=0,
        description="Sem valor, usa o estoque mínimo de cada produto."
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


@router.get(
    "/compras",
    response_model=RelatorioComprasResposta
)
def obter_relatorio_compras(
    data_inicio: date | None = None,
    data_fim: date | None = None,
    fornecedor_id: int | None = Query(
        default=None,
        gt=0
    )
):
    if data_inicio and data_fim and data_inicio > data_fim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A data inicial não pode ser posterior à data final."
        )

    relatorio = gerar_relatorio_compras(
        data_inicio=data_inicio,
        data_fim=data_fim,
        fornecedor_id=fornecedor_id
    )

    if relatorio is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível gerar o relatório de compras."
        )

    return relatorio
