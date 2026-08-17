from fastapi import APIRouter, HTTPException, status

from backend.repositorio import (
    atualizar_produto,
    buscar_produto_por_id,
    cadastrar_produto,
    excluir_produto,
    listar_produtos
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
def obter_produtos():
    return listar_produtos()


@router.get(
    "/{id_produto}",
    response_model=ProdutoResposta
)
def obter_produto(id_produto: int):
    produto = buscar_produto_por_id(id_produto)

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
    produto = cadastrar_produto(
        dados.nome,
        dados.categoria,
        dados.quantidade,
        dados.preco
    )

    if produto is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível cadastrar o produto."
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
    produto = atualizar_produto(
        id_produto,
        dados.nome,
        dados.categoria,
        dados.quantidade,
        dados.preco
    )

    if produto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado."
        )

    return produto


@router.delete(
    "/{id_produto}",
    status_code=status.HTTP_204_NO_CONTENT
)
def remover_produto(id_produto: int):
    excluido = excluir_produto(id_produto)

    if not excluido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado."
        )

    return None