from datetime import date

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from backend.autenticacao import obter_usuario_atual
from backend.permissoes import exigir
from backend.repositorio_compra import (
    buscar_compra,
    buscar_compra_por_solicitacao,
    listar_compras,
    registrar_compra,
)
from backend.repositorio_recebimento import (
    listar_recebimentos,
    registrar_recebimento,
)
from backend.schemas.compra import (
    CompraCriacao,
    CompraResposta,
    SituacaoRecebimento,
)
from backend.schemas.recebimento import (
    RecebimentoCriacao,
    RecebimentoResposta,
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
    "compra_ja_recebida": (
        status.HTTP_409_CONFLICT,
        "Todos os itens desta compra já foram recebidos."
    ),
    "status_nao_permite_recebimento": (
        status.HTTP_409_CONFLICT,
        "Registre a compra antes de receber os materiais."
    ),
    "data_anterior_a_compra": (
        status.HTTP_400_BAD_REQUEST,
        "A data do recebimento não pode ser anterior à data da compra."
    ),
    "produto_fora_da_compra": (
        status.HTTP_400_BAD_REQUEST,
        "O recebimento só pode conter produtos da compra."
    ),
    "quantidade_maior_que_pendente": (
        status.HTTP_400_BAD_REQUEST,
        "A quantidade recebida é maior que a quantidade pendente."
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


@router.post(
    "/solicitacoes-compra/{solicitacao_id}/compra",
    dependencies=[exigir("compras.registrar")],
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
        tratar_erro(erro, "Não foi possível registrar a compra.")

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
    situacao_recebimento: SituacaoRecebimento | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
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
    if data_inicio and data_fim and data_inicio > data_fim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A data inicial não pode ser posterior à data final."
        )

    return listar_compras(
        fornecedor_id=fornecedor_id,
        situacao_recebimento=situacao_recebimento,
        data_inicio=data_inicio,
        data_fim=data_fim,
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


@router.post(
    "/solicitacoes-compra/{solicitacao_id}/compra/recebimentos",
    dependencies=[exigir("recebimentos.registrar")],
    response_model=RecebimentoResposta,
    status_code=status.HTTP_201_CREATED
)
def receber(
    solicitacao_id: int,
    dados: RecebimentoCriacao,
    usuario=Depends(obter_usuario_atual)
):
    itens = (
        [
            {
                "produto_id": item.produto_id,
                "quantidade": item.quantidade
            }
            for item in dados.itens
        ]
        if dados.itens is not None
        else None
    )

    recebimento, erro = registrar_recebimento(
        solicitacao_id=solicitacao_id,
        recebedor_id=usuario[0],
        data_recebimento=dados.data_recebimento,
        nota_fiscal=dados.nota_fiscal,
        observacao=dados.observacao,
        itens=itens
    )

    if erro is not None or recebimento is None:
        tratar_erro(erro, "Não foi possível registrar o recebimento.")

    return recebimento


@router.get(
    "/solicitacoes-compra/{solicitacao_id}/compra/recebimentos",
    response_model=list[RecebimentoResposta]
)
def listar_da_compra(solicitacao_id: int):
    recebimentos = listar_recebimentos(solicitacao_id)

    if recebimentos is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compra não encontrada."
        )

    return recebimentos
