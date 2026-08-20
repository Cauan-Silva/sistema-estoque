from pydantic import BaseModel, Field


class CategoriaCriar(BaseModel):
    nome: str = Field(
        min_length=2,
        max_length=100
    )


class CategoriaAtualizar(BaseModel):
    nome: str = Field(
        min_length=2,
        max_length=100
    )


class CategoriaResposta(BaseModel):
    id: int
    nome: str