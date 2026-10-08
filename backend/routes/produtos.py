import psycopg2
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status
)

from backend.autenticacao import obter_usuario_atual
from backend.repositorio import (
    atualizar_produto,
    buscar_produto_por_id,
    cadastrar_produto,
    excluir_produto,
    listar_produtos
)

from backend.repositorio_categoria import (
    buscar_categoria
)

from backend.repositorio_fornecedor import (
    buscar_fornecedor
)

from backend.schemas.produto import (
    ProdutoAtualizar,
    ProdutoCriar,
    ProdutoResposta
)


router = APIRouter(
    prefix="/produtos",
    tags=["Produtos"],
    dependencies=[
        Depends(obter_usuario_atual)
    ]
)


def validar_fornecedor(
    fornecedor_id: int | None,
    permitir_inativo: bool = False
):
    if fornecedor_id is None:
        return

    fornecedor = buscar_fornecedor(fornecedor_id)

    if fornecedor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fornecedor não encontrado."
        )

    if not fornecedor[7] and not permitir_inativo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fornecedor inativo."
        )


@router.get(
    "",
    response_model=list[ProdutoResposta]
)
def obter_produtos(
    busca: str | None = Query(
        default=None,
        min_length=1
    ),
    categoria_id: int | None = Query(
        default=None,
        gt=0
    ),
    fornecedor_id: int | None = Query(
        default=None,
        gt=0
    ),
    estoque_baixo: bool = False,
    limite_estoque: int = Query(
        default=5,
        ge=0
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
    return listar_produtos(
        busca=busca,
        categoria_id=categoria_id,
        fornecedor_id=fornecedor_id,
        estoque_baixo=estoque_baixo,
        limite_estoque=limite_estoque,
        pagina=pagina,
        tamanho=tamanho
    )


@router.get(
    "/{id_produto}",
    response_model=ProdutoResposta
)
def obter_produto(id_produto: int):
    produto = buscar_produto_por_id(
        id_produto
    )

    if produto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado."
        )

    return produto


@router.post(
    "",
    response_model=ProdutoResposta,
    status_code=status.HTTP_201_CREATED
)
def criar_produto(dados: ProdutoCriar):
    categoria = buscar_categoria(
        dados.categoria_id
    )

    if categoria is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada."
        )

    validar_fornecedor(dados.fornecedor_id)

    produto = cadastrar_produto(
        dados.nome.strip(),
        dados.categoria_id,
        dados.quantidade,
        dados.preco,
        dados.fornecedor_id
    )

    if produto is None:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Não foi possível cadastrar "
                "o produto."
            )
        )

    return produto


@router.put(
    "/{id_produto}",
    response_model=ProdutoResposta
)
def editar_produto(
    id_produto: int,
    dados: ProdutoAtualizar
):
    produto_existente = buscar_produto_por_id(
        id_produto
    )

    if produto_existente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado."
        )

    categoria = buscar_categoria(
        dados.categoria_id
    )

    if categoria is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada."
        )

    validar_fornecedor(
        dados.fornecedor_id,
        permitir_inativo=(
            dados.fornecedor_id
            == produto_existente.fornecedor_id
        )
    )

    produto = atualizar_produto(
        id_produto,
        dados.nome.strip(),
        dados.categoria_id,
        dados.quantidade,
        dados.preco,
        dados.fornecedor_id
    )

    if produto is None:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Não foi possível atualizar "
                "o produto."
            )
        )

    return produto


@router.delete(
    "/{id_produto}",
    status_code=status.HTTP_204_NO_CONTENT
)
def remover_produto(id_produto: int):
    try:
        excluido = excluir_produto(
            id_produto
        )

    except psycopg2.errors.ForeignKeyViolation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Não é possível excluir um produto "
                "vinculado a solicitações de compra."
            )
        )

    if not excluido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado."
        )

    return None