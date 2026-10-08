from datetime import date, datetime

from typing import Literal

from pydantic import BaseModel, Field, model_validator


SituacaoRecebimento = Literal["PENDENTE", "PARCIAL", "COMPLETO"]


class CompraCriacao(BaseModel):
    numero_pedido: str | None = Field(
        default=None,
        max_length=50
    )
    data_compra: date | None = None
    previsao_entrega: date | None = None
    observacao: str | None = Field(
        default=None,
        max_length=500
    )

    @model_validator(mode="after")
    def validar_datas(self):
        if (
            self.data_compra is not None
            and self.previsao_entrega is not None
            and self.previsao_entrega < self.data_compra
        ):
            raise ValueError(
                "A previsão de entrega não pode ser anterior "
                "à data da compra."
            )

        return self


class ItemCompraResposta(BaseModel):
    produto_id: int
    produto: str
    quantidade: int
    preco_unitario: float
    subtotal: float
    quantidade_recebida: int
    quantidade_pendente: int


class CompraResposta(BaseModel):
    id: int
    solicitacao_id: int
    cotacao_id: int
    fornecedor_id: int
    fornecedor: str
    comprador_id: int
    comprador: str
    numero_pedido: str | None
    data_compra: date
    previsao_entrega: date
    valor_itens: float
    frete: float
    valor_total: float
    observacao: str | None
    data_criacao: datetime
    situacao_recebimento: SituacaoRecebimento
    ultimo_recebimento: date | None
    entregue_no_prazo: bool | None
    forma_pagamento_id: int | None = None
    forma_pagamento: str | None = None
    itens: list[ItemCompraResposta]
