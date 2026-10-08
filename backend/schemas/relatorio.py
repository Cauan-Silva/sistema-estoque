from datetime import date

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

class ComprasFornecedorResposta(BaseModel):
    fornecedor_id: int
    fornecedor: str
    compras: int
    valor_total: float
    entregas_no_prazo: int
    entregas_atrasadas: int


class ComprasProdutoResposta(BaseModel):
    produto_id: int
    produto: str
    quantidade: int
    valor_total: float
    preco_medio: float
    menor_preco: float
    maior_preco: float


class ComprasMesResposta(BaseModel):
    mes: str
    compras: int
    valor_total: float


class RelatorioComprasResposta(BaseModel):
    data_inicio: date | None
    data_fim: date | None
    total_compras: int
    valor_total: float
    valor_itens: float
    frete_total: float
    ticket_medio: float
    compras_recebidas: int
    compras_parciais: int
    compras_pendentes: int
    entregas_no_prazo: int
    entregas_atrasadas: int
    percentual_no_prazo: float | None
    prazo_medio_entrega_dias: float | None
    atrasadas_em_aberto: int
    por_fornecedor: list[ComprasFornecedorResposta]
    por_produto: list[ComprasProdutoResposta]
    por_mes: list[ComprasMesResposta]
