from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


StatusSolicitacao = Literal[
    "ABERTA",
    "EM_COTACAO",
    "APROVADA",
    "REPROVADA",
    "COMPRADA",
    "RECEBIDA",
    "CANCELADA",
]


class ItemSolicitacaoEntrada(BaseModel):
    produto_id: int = Field(gt=0)
    quantidade: int = Field(gt=0)


class SolicitacaoCompraEntrada(BaseModel):
    observacao: str | None = Field(
        default=None,
        max_length=500
    )
    itens: list[ItemSolicitacaoEntrada] = Field(
        min_length=1
    )

    @field_validator("itens")
    @classmethod
    def validar_produtos_repetidos(cls, itens):
        produto_ids = [item.produto_id for item in itens]

        if len(produto_ids) != len(set(produto_ids)):
            raise ValueError(
                "Cada produto pode aparecer apenas uma vez na solicitação."
            )

        return itens


class SolicitacaoCompraCriacao(SolicitacaoCompraEntrada):
    pass


class SolicitacaoCompraAtualizacao(SolicitacaoCompraEntrada):
    pass


class ItemSolicitacaoResposta(BaseModel):
    id: int
    produto_id: int
    produto: str
    quantidade: int


class SolicitacaoCompraResposta(BaseModel):
    id: int
    solicitante_id: int
    solicitante: str
    status: StatusSolicitacao
    observacao: str | None
    data_criacao: datetime
    data_atualizacao: datetime
    itens: list[ItemSolicitacaoResposta]
