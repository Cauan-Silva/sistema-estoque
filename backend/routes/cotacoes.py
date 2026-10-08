from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from backend.autenticacao import obter_usuario_atual
from backend.repositorio_cotacao import (
    atualizar_cotacao,
    buscar_cotacao,
    comparar_cotacoes,
    criar_cotacao,
    excluir_cotacao,
    listar_cotacoes,
)
from backend.schemas.cotacao import (
    ComparacaoCotacoesResposta,
    CotacaoAtualizacao,
    CotacaoCriacao,
    CotacaoResposta,
)


router = APIRouter(
    prefix="/solicitacoes-compra/{solicitacao_id}/cotacoes",
    tags=["Cotações"],
    dependencies=[
        Depends(obter_usuario_atual)
    ]
)


ERROS = {
    "solicitacao_nao_encontrada": (
        status.HTTP_404_NOT_FOUND,
        "Solicitação de compra não encontrada."
    ),
    "cotacao_nao_encontrada": (
        status.HTTP_404_NOT_FOUND,
        "Cotação não encontrada."
    ),
    "fornecedor_nao_encontrado": (
        status.HTTP_404_NOT_FOUND,
        "Fornecedor não encontrado."
    ),
    "fornecedor_inativo": (
        status.HTTP_400_BAD_REQUEST,
        "Fornecedor inativo."
    ),
    "produto_fora_da_solicitacao": (
        status.HTTP_400_BAD_REQUEST,
        "A cotação só pode conter produtos da solicitação."
    ),
    "cotacao_duplicada": (
        status.HTTP_409_CONFLICT,
        "Este fornecedor já possui cotação para esta solicitação."
    ),
    "solicitacao_nao_permite_cotacao": (
        status.HTTP_409_CONFLICT,
        "A solicitação não permite alterar cotações no status atual."
    ),
}


def tratar_erro(erro: str | None, mensagem_padrao: str):
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
            "preco_unitario": item.preco_unitario
        }
        for item in itens
    ]


@router.post(
    "",
    response_model=CotacaoResposta,
    status_code=status.HTTP_201_CREATED
)
def criar(solicitacao_id: int, dados: CotacaoCriacao):
    cotacao, erro = criar_cotacao(
        solicitacao_id=solicitacao_id,
        fornecedor_id=dados.fornecedor_id,
        frete=dados.frete,
        prazo_entrega_dias=dados.prazo_entrega_dias,
        validade=dados.validade,
        observacao=dados.observacao,
        itens=itens_para_dict(dados.itens)
    )

    if erro is not None or cotacao is None:
        tratar_erro(erro, "Não foi possível registrar a cotação.")

    return cotacao


@router.get(
    "",
    response_model=list[CotacaoResposta]
)
def listar(solicitacao_id: int):
    cotacoes = listar_cotacoes(solicitacao_id)

    if cotacoes is None:
        tratar_erro("solicitacao_nao_encontrada", "")

    return cotacoes


@router.get(
    "/comparacao",
    response_model=ComparacaoCotacoesResposta
)
def comparar(solicitacao_id: int):
    comparacao = comparar_cotacoes(solicitacao_id)

    if comparacao is None:
        tratar_erro("solicitacao_nao_encontrada", "")

    return comparacao


@router.get(
    "/{cotacao_id}",
    response_model=CotacaoResposta
)
def buscar(solicitacao_id: int, cotacao_id: int):
    cotacao = buscar_cotacao(solicitacao_id, cotacao_id)

    if cotacao is None:
        tratar_erro("cotacao_nao_encontrada", "")

    return cotacao


@router.put(
    "/{cotacao_id}",
    response_model=CotacaoResposta
)
def editar(
    solicitacao_id: int,
    cotacao_id: int,
    dados: CotacaoAtualizacao
):
    cotacao, erro = atualizar_cotacao(
        solicitacao_id=solicitacao_id,
        cotacao_id=cotacao_id,
        frete=dados.frete,
        prazo_entrega_dias=dados.prazo_entrega_dias,
        validade=dados.validade,
        observacao=dados.observacao,
        itens=itens_para_dict(dados.itens)
    )

    if erro is not None or cotacao is None:
        tratar_erro(erro, "Não foi possível atualizar a cotação.")

    return cotacao


@router.delete(
    "/{cotacao_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def remover(solicitacao_id: int, cotacao_id: int):
    erro = excluir_cotacao(solicitacao_id, cotacao_id)

    if erro is not None:
        tratar_erro(erro, "Não foi possível excluir a cotação.")

    return None
