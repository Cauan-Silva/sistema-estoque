from pydantic import BaseModel


class ResumoEstoqueResposta(BaseModel):
    total_produtos: int
    total_categorias: int
    unidades_em_estoque: int
    produtos_estoque_baixo: int
    valor_total_estoque: float
    total_entradas: int
    total_saidas: int


class ProdutoValorEstoqueResposta(BaseModel):
    id: int
    nome: str
    categoria: str
    quantidade: int
    preco: float
    valor_estoque: float