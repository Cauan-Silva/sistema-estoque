from pydantic import BaseModel, Field


class ProdutoBase(BaseModel):
    nome: str = Field(min_length=2, max_length=150)
    categoria: str = Field(min_length=2, max_length=100)
    quantidade: int = Field(ge=0)
    preco: float = Field(ge=0)


class ProdutoCriar(ProdutoBase):
    pass


class ProdutoAtualizar(ProdutoBase):
    pass


class ProdutoResposta(ProdutoBase):
    id: int

    class Config:
        from_attributes = True