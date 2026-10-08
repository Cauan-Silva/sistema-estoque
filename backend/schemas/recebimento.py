from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


class ItemRecebimentoEntrada(BaseModel):
    produto_id: int = Field(gt=0)
    quantidade: int = Field(gt=0)


class RecebimentoCriacao(BaseModel):
    data_recebimento: date | None = None
    nota_fiscal: str | None = Field(
        default=None,
        max_length=50
    )
    observacao: str | None = Field(
        default=None,
        max_length=500
    )
    itens: list[ItemRecebimentoEntrada] | None = Field(
        default=None,
        min_length=1
    )

    @field_validator("itens")
    @classmethod
    def validar_produtos_repetidos(cls, itens):
        if itens is None:
            return itens

        produto_ids = [item.produto_id for item in itens]

        if len(produto_ids) != len(set(produto_ids)):
            raise ValueError(
                "Cada produto pode aparecer apenas uma vez no recebimento."
            )

        return itens


class ItemRecebimentoResposta(BaseModel):
    produto_id: int
    produto: str
    quantidade: int
    movimentacao_id: int | None


class RecebimentoResposta(BaseModel):
    id: int
    compra_id: int
    solicitacao_id: int
    recebedor_id: int
    recebedor: str
    data_recebimento: date
    nota_fiscal: str | None
    observacao: str | None
    data_criacao: datetime
    itens: list[ItemRecebimentoResposta]
