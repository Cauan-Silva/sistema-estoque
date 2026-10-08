from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from backend.autenticacao import obter_usuario_atual
from backend.repositorio_compra import (
    buscar_compra,
    buscar_compra_por_solicitacao,
    listar_compras,
    registrar_compra,
)
from backend.schemas.compra import (
    CompraCriacao,
    CompraResposta,
)


router = APIRouter(
    tags=["Compras"],
    dependencies=[
        Depends(obter_usuario_atual)
    ]
)


ERROS = {
    "solicitacao_nao_encontrada": (
        status.HTTP_404_NOT_FOUND,
        "Solicitação de compra não encontrada."
    ),
    "status_nao_permite_compra": (
        status.HTTP_409_CONFLICT,
        "Apenas solicitações aprovadas podem ter a compra registrada."
    ),
    "previsao_invalida": (
        status.HTTP_400_BAD_REQUEST,
        "A previsão de entrega não pode ser anterior à data da compra."
    ),
}


@router.post(
    "/solicitacoes-compra/{solicitacao_id}/compra",
    response_model=CompraResposta,
    status_code=status.HTTP_201_CREATED
)
def registrar(
    solicitacao_id: int,
    dados: CompraCriacao,
    usuario=Depends(obter_usuario_atual)
):
    compra, erro = registrar_compra(
        solicitacao_id=solicitacao_id,
        comprador_id=usuario[0],
        numero_pedido=dados.numero_pedido,
        data_compra=dados.data_compra,
        previsao_entrega=dados.previsao_entrega,
        observacao=dados.observacao
    )

    if erro is not None or compra is None:
        codigo, detalhe = ERROS.get(
            erro,
            (
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "Não foi possível registrar a compra."
            )
        )

        raise HTTPException(
            status_code=codigo,
            detail=detalhe
        )

    return compra


@router.get(
    "/solicitacoes-compra/{solicitacao_id}/compra",
    response_model=CompraResposta
)
def buscar_da_solicitacao(solicitacao_id: int):
    compra = buscar_compra_por_solicitacao(solicitacao_id)

    if compra is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compra não encontrada."
        )

    return compra


@router.get(
    "/compras",
    response_model=list[CompraResposta]
)
def listar(
    fornecedor_id: int | None = Query(
        default=None,
        gt=0
    ),
    pagina: int = Query(
        default=1,
        ge=1
    ),
    tamanho: int = Query(
        default=10,
        ge=1,
        le=100
    )
):
    return listar_compras(
        fornecedor_id=fornecedor_id,
        pagina=pagina,
        tamanho=tamanho
    )


@router.get(
    "/compras/{compra_id}",
    response_model=CompraResposta
)
def buscar(compra_id: int):
    compra = buscar_compra(compra_id)

    if compra is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compra não encontrada."
        )

    return compra
