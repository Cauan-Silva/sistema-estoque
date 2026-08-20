from fastapi import APIRouter, HTTPException, status
import psycopg2

from backend.repositorio_categoria import (
    buscar_categoria,
    cadastrar_categoria,
    editar_categoria,
    excluir_categoria,
    listar_categorias
)

from backend.schemas.categoria import (
    CategoriaAtualizar,
    CategoriaCriar,
    CategoriaResposta
)


router = APIRouter(
    prefix="/categorias",
    tags=["Categorias"]
)


@router.get(
    "",
    response_model=list[CategoriaResposta]
)
def obter_categorias():
    return listar_categorias()


@router.get(
    "/{id_categoria}",
    response_model=CategoriaResposta
)
def obter_categoria(id_categoria: int):
    categoria = buscar_categoria(id_categoria)

    if categoria is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada."
        )

    return categoria


@router.post(
    "",
    response_model=CategoriaResposta,
    status_code=status.HTTP_201_CREATED
)
def criar_categoria(dados: CategoriaCriar):
    try:
        return cadastrar_categoria(
            dados.nome.strip()
        )

    except psycopg2.errors.UniqueViolation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Categoria já cadastrada."
        )


@router.put(
    "/{id_categoria}",
    response_model=CategoriaResposta
)
def atualizar_categoria(
    id_categoria: int,
    dados: CategoriaAtualizar
):
    try:
        categoria = editar_categoria(
            id_categoria,
            dados.nome.strip()
        )

    except psycopg2.errors.UniqueViolation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma categoria com esse nome."
        )

    if categoria is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada."
        )

    return categoria


@router.delete(
    "/{id_categoria}",
    status_code=status.HTTP_204_NO_CONTENT
)
def remover_categoria(id_categoria: int):
    try:
        excluida = excluir_categoria(
            id_categoria
        )

    except psycopg2.errors.ForeignKeyViolation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Não é possível excluir uma categoria "
                "que possui produtos vinculados."
            )
        )

    if not excluida:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada."
        )

    return None