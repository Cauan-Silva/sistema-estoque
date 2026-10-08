from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


class ItemCotacaoEntrada(BaseModel):
    produto_id: int = Field(gt=0)
    preco_unitario: float = Field(ge=0)


class CotacaoBase(BaseModel):
    frete: float = Field(
        default=0,
        ge=0
    )
    prazo_entrega_dias: int = Field(ge=0)
    validade: date | None = None
    observacao: str | None = Field(
        default=None,
        max_length=500
    )
    itens: list[ItemCotacaoEntrada] = Field(
        min_length=1
    )

    @field_validator("itens")
    @classmethod
    def validar_produtos_repetidos(cls, itens):
        produto_ids = [item.produto_id for item in itens]

        if len(produto_ids) != len(set(produto_ids)):
            raise ValueError(
                "Cada produto pode aparecer apenas uma vez na cotação."
            )

        return itens


class CotacaoCriacao(CotacaoBase):
    fornecedor_id: int = Field(gt=0)


class CotacaoAtualizacao(CotacaoBase):
    pass


class ItemCotacaoResposta(BaseModel):
    produto_id: int
    produto: str
    quantidade: int
    preco_unitario: float
    subtotal: float


class CotacaoResposta(BaseModel):
    id: int
    solicitacao_id: int
    fornecedor_id: int
    fornecedor: str
    frete: float
    prazo_entrega_dias: int
    validade: date | None
    observacao: str | None
    data_criacao: datetime
    data_atualizacao: datetime
    itens: list[ItemCotacaoResposta]
    valor_itens: float
    valor_total: float


class CotacaoDestaque(BaseModel):
    cotacao_id: int
    fornecedor_id: int
    fornecedor: str
    valor_total: float
    frete: float
    prazo_entrega_dias: int
    validade: date | None


class CotacaoComparada(CotacaoDestaque):
    valor_itens: float
    itens_cotados: int
    cobre_todos_itens: bool
    vencida: bool
    elegivel: bool


class MelhorPrecoProduto(BaseModel):
    produto_id: int
    produto: str
    quantidade: int
    quantidade_ofertas: int
    melhor_preco_unitario: float | None
    cotacao_id: int | None
    fornecedor_id: int | None
    fornecedor: str | None


class ComparacaoCotacoesResposta(BaseModel):
    solicitacao_id: int
    status_solicitacao: str
    total_cotacoes: int
    cotacoes_elegiveis: int
    menor_valor_total: CotacaoDestaque | None
    menor_prazo: CotacaoDestaque | None
    menor_frete: CotacaoDestaque | None
    cotacoes: list[CotacaoComparada]
    por_produto: list[MelhorPrecoProduto]
