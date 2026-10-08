from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from backend.autenticacao import obter_usuario_atual
from backend.repositorio_solicitacao_compra import (
    atualizar_solicitacao,
    buscar_solicitacao,
    cancelar_solicitacao,
    criar_solicitacao,
    listar_solicitacoes,
)
from backend.schemas.solicitacao_compra import (
    SolicitacaoCompraAtualizacao,
    SolicitacaoCompraCriacao,
    SolicitacaoCompraResposta,
    StatusSolicitacao,
)


router = APIRouter(
    prefix="/solicitacoes-compra",
    tags=["Solicitações de compra"],
    dependencies=[
        Depends(obter_usuario_atual)
    ]
)


ERROS = {
    "produto_nao_encontrado": (
        status.HTTP_404_NOT_FOUND,
        "Produto não encontrado."
    ),
    "solicitacao_nao_encontrada": (
        status.HTTP_404_NOT_FOUND,
        "Solicitação de compra não encontrada."
    ),
    "status_nao_permite_alteracao": (
        status.HTTP_409_CONFLICT,
        "Apenas solicitações abertas podem ser alteradas."
    ),
    "status_nao_permite_cancelamento": (
        status.HTTP_409_CONFLICT,
        "Esta solicitação não pode mais ser cancelada."
    ),
}


def tratar_erro(erro: str, mensagem_padrao: str):
    codigo, detalhe = ERROS.get(
        erro,
        (
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            mensagem_padrao
        )
    )

    raise HTTPException(
        status_code=codigo,
        detail=detalhe
    )


def itens_para_dict(itens):
    return [
        {
            "produto_id": item.produto_id,
            "quantidade": item.quantidade
        }
        for item in itens
    ]


@router.post(
    "",
    response_model=SolicitacaoCompraResposta,
    status_code=status.HTTP_201_CREATED
)
def criar(
    dados: SolicitacaoCompraCriacao,
    usuario=Depends(obter_usuario_atual)
):
    solicitacao, erro = criar_solicitacao(
        solicitante_id=usuario[0],
        observacao=dados.observacao,
        itens=itens_para_dict(dados.itens)
    )

    if erro is not None or solicitacao is None:
        tratar_erro(
            erro,
            "Não foi possível criar a solicitação de compra."
        )

    return solicitacao


@router.get(
    "",
    response_model=list[SolicitacaoCompraResposta]
)
def listar(
    status_solicitacao: StatusSolicitacao | None = Query(
        default=None,
        alias="status"
    ),
    apenas_minhas: bool = False,
    pagina: int = Query(
        default=1,
        ge=1
    ),
    tamanho: int = Query(
        default=10,
        ge=1,
        le=100
    ),
    usuario=Depends(obter_usuario_atual)
):
    return listar_solicitacoes(
        status=status_solicitacao,
        solicitante_id=usuario[0] if apenas_minhas else None,
        pagina=pagina,
        tamanho=tamanho
    )


@router.get(
    "/{solicitacao_id}",
    response_model=SolicitacaoCompraResposta
)
def buscar(solicitacao_id: int):
    solicitacao = buscar_solicitacao(solicitacao_id)

    if solicitacao is None:
        tratar_erro(
            "solicitacao_nao_encontrada",
            ""
        )

    return solicitacao


@router.put(
    "/{solicitacao_id}",
    response_model=SolicitacaoCompraResposta
)
def editar(
    solicitacao_id: int,
    dados: SolicitacaoCompraAtualizacao
):
    solicitacao, erro = atualizar_solicitacao(
        solicitacao_id=solicitacao_id,
        observacao=dados.observacao,
        itens=itens_para_dict(dados.itens)
    )

    if erro is not None or solicitacao is None:
        tratar_erro(
            erro,
            "Não foi possível atualizar a solicitação de compra."
        )

    return solicitacao


@router.patch(
    "/{solicitacao_id}/cancelar",
    response_model=SolicitacaoCompraResposta
)
def cancelar(solicitacao_id: int):
    solicitacao, erro = cancelar_solicitacao(solicitacao_id)

    if erro is not None or solicitacao is None:
        tratar_erro(
            erro,
            "Não foi possível cancelar a solicitação de compra."
        )

    return solicitacao
