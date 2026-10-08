from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from backend.autenticacao import obter_usuario_atual
from backend.permissoes import exigir
from backend.repositorio_aprovacao import (
    aprovar_solicitacao,
    reprovar_solicitacao,
)
from backend.repositorio_solicitacao_compra import (
    atualizar_solicitacao,
    buscar_solicitacao,
    cancelar_solicitacao,
    criar_solicitacao,
    listar_solicitacoes,
)
from backend.schemas.solicitacao_compra import (
    AprovacaoEntrada,
    ReprovacaoEntrada,
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
    "decisao_propria": (
        status.HTTP_403_FORBIDDEN,
        "Você não pode aprovar ou reprovar uma solicitação criada por você."
    ),
    "status_nao_permite_decisao": (
        status.HTTP_409_CONFLICT,
        "A solicitação não pode ser aprovada ou reprovada no status atual."
    ),
    "cotacao_nao_encontrada": (
        status.HTTP_404_NOT_FOUND,
        "Cotação não encontrada."
    ),
    "cotacao_incompleta": (
        status.HTTP_400_BAD_REQUEST,
        "A cotação não cobre todos os itens da solicitação."
    ),
    "cotacao_vencida": (
        status.HTTP_400_BAD_REQUEST,
        "A cotação está vencida."
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
    dependencies=[exigir("solicitacoes.editar")],
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
    dependencies=[exigir("solicitacoes.editar")],
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
    dependencies=[exigir("solicitacoes.editar")],
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


@router.patch(
    "/{solicitacao_id}/aprovar",
    dependencies=[exigir("compras.aprovar")],
    response_model=SolicitacaoCompraResposta
)
def aprovar(
    solicitacao_id: int,
    dados: AprovacaoEntrada,
    usuario=Depends(obter_usuario_atual)
):
    solicitacao, erro = aprovar_solicitacao(
        solicitacao_id=solicitacao_id,
        cotacao_id=dados.cotacao_id,
        usuario_id=usuario[0],
        justificativa=dados.justificativa
    )

    if erro is not None or solicitacao is None:
        tratar_erro(
            erro,
            "Não foi possível aprovar a solicitação de compra."
        )

    return solicitacao


@router.patch(
    "/{solicitacao_id}/reprovar",
    dependencies=[exigir("compras.aprovar")],
    response_model=SolicitacaoCompraResposta
)
def reprovar(
    solicitacao_id: int,
    dados: ReprovacaoEntrada,
    usuario=Depends(obter_usuario_atual)
):
    solicitacao, erro = reprovar_solicitacao(
        solicitacao_id=solicitacao_id,
        usuario_id=usuario[0],
        justificativa=dados.justificativa.strip()
    )

    if erro is not None or solicitacao is None:
        tratar_erro(
            erro,
            "Não foi possível reprovar a solicitação de compra."
        )

    return solicitacao
