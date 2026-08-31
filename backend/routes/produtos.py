from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    status
)

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

from backend.schemas.produto import (
    ProdutoAtualizar,
    ProdutoCriar,
    ProdutoResposta
)


router = APIRouter(
    prefix="/produtos",
    tags=["Produtos"]
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
    estoque_baixo: bool = False,
    limite_estoque: int = Query(
        default=5,
        ge=0
    )
):
    return listar_produtos(
        busca=busca,
        categoria_id=categoria_id,
        estoque_baixo=estoque_baixo,
        limite_estoque=limite_estoque
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

    produto = cadastrar_produto(
        dados.nome.strip(),
        dados.categoria_id,
        dados.quantidade,
        dados.preco
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

    produto = atualizar_produto(
        id_produto,
        dados.nome.strip(),
        dados.categoria_id,
        dados.quantidade,
        dados.preco
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
    excluido = excluir_produto(
        id_produto
    )

    if not excluido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado."
        )

    return None