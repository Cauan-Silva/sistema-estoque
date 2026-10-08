from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from backend.autenticacao import obter_usuario_atual
from backend.repositorio_forma_pagamento import (
    alterar_status_forma_pagamento,
    atualizar_forma_pagamento,
    buscar_forma_pagamento,
    cadastrar_forma_pagamento,
    listar_formas_pagamento,
)
from backend.schemas.forma_pagamento import (
    FormaPagamentoEntrada,
    FormaPagamentoResposta,
    FormaPagamentoStatus,
    FormasPagamentoPagina,
    TipoFormaPagamento,
)


router = APIRouter(
    prefix="/formas-pagamento",
    tags=["Formas de pagamento"],
    dependencies=[
        Depends(obter_usuario_atual)
    ]
)


ERROS = {
    "forma_nao_encontrada": (
        status.HTTP_404_NOT_FOUND,
        "Forma de pagamento não encontrada."
    ),
    "codigo_duplicado": (
        status.HTTP_409_CONFLICT,
        "Já existe uma forma de pagamento com esse código."
    ),
}


def tratar_erro(erro, mensagem_padrao):
    codigo, detalhe = ERROS.get(
        erro,
        (status.HTTP_500_INTERNAL_SERVER_ERROR, mensagem_padrao)
    )

    raise HTTPException(status_code=codigo, detail=detalhe)


@router.get("", response_model=FormasPagamentoPagina)
def listar(
    busca: str | None = Query(default=None, max_length=100),
    tipo: TipoFormaPagamento | None = None,
    ativo: bool | None = None,
    ordem: Literal["codigo", "titulo", "tipo"] = "codigo",
    decrescente: bool = False,
    pagina: int = Query(default=1, ge=1),
    tamanho: int = Query(default=10, ge=1, le=100)
):
    resultado = listar_formas_pagamento(
        busca=busca.strip() if busca else None,
        tipo=tipo,
        ativo=ativo,
        ordem=ordem,
        decrescente=decrescente,
        pagina=pagina,
        tamanho=tamanho
    )

    if resultado is None:
        tratar_erro(None, "Não foi possível listar as formas de pagamento.")

    return resultado


@router.get("/{forma_id}", response_model=FormaPagamentoResposta)
def buscar(forma_id: int):
    forma = buscar_forma_pagamento(forma_id)

    if forma is None:
        tratar_erro("forma_nao_encontrada", "")

    return forma


@router.post(
    "",
    response_model=FormaPagamentoResposta,
    status_code=status.HTTP_201_CREATED
)
def criar(dados: FormaPagamentoEntrada):
    forma, erro = cadastrar_forma_pagamento(
        dados.codigo.strip(),
        dados.titulo.strip(),
        dados.tipo,
        dados.parcelas,
        dados.intervalo_dias
    )

    if erro is not None:
        tratar_erro(erro, "Não foi possível cadastrar a forma de pagamento.")

    return forma


@router.put("/{forma_id}", response_model=FormaPagamentoResposta)
def editar(forma_id: int, dados: FormaPagamentoEntrada):
    forma, erro = atualizar_forma_pagamento(
        forma_id,
        dados.codigo.strip(),
        dados.titulo.strip(),
        dados.tipo,
        dados.parcelas,
        dados.intervalo_dias
    )

    if erro is not None:
        tratar_erro(erro, "Não foi possível atualizar a forma de pagamento.")

    return forma


@router.patch("/{forma_id}/status", response_model=FormaPagamentoResposta)
def alterar_status(forma_id: int, dados: FormaPagamentoStatus):
    forma, erro = alterar_status_forma_pagamento(forma_id, dados.ativo)

    if erro is not None:
        tratar_erro(erro, "Não foi possível alterar a forma de pagamento.")

    return forma
