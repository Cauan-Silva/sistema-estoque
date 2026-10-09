from datetime import date

from pydantic import BaseModel, Field, field_validator, model_validator


class ItemOrcamentoEntrada(BaseModel):
    produto_id: int = Field(gt=0)
    preco_unitario: float = Field(ge=0)
    codigo_fornecedor: str | None = Field(default=None, max_length=100)
    descricao_fornecedor: str | None = Field(default=None, max_length=300)


class OrcamentoEntrada(BaseModel):
    fornecedor_id: int = Field(gt=0)
    frete: float = Field(default=0, ge=0)
    prazo_entrega_dias: int = Field(ge=0)
    validade: date | None = None
    observacao: str | None = Field(default=None, max_length=500)
    forma_pagamento_id: int | None = Field(default=None, gt=0)
    itens: list[ItemOrcamentoEntrada] = Field(min_length=1)

    @field_validator("itens")
    @classmethod
    def sem_produto_repetido(cls, itens):
        ids = [item.produto_id for item in itens]
        if len(ids) != len(set(ids)):
            raise ValueError("Cada produto pode aparecer apenas uma vez em um orçamento.")
        return itens


class ItemSolicitacaoEntrada(BaseModel):
    produto_id: int = Field(gt=0)
    quantidade: int = Field(gt=0)


class SolicitacaoPorOrcamentos(BaseModel):
    observacao: str | None = Field(default=None, max_length=500)
    itens: list[ItemSolicitacaoEntrada] = Field(min_length=1)
    orcamentos: list[OrcamentoEntrada] = Field(default_factory=list)

    @model_validator(mode="after")
    def validar_conjunto(self):
        produtos = [item.produto_id for item in self.itens]
        if len(produtos) != len(set(produtos)):
            raise ValueError("Cada produto pode aparecer apenas uma vez na solicitação.")

        fornecedores = [orcamento.fornecedor_id for orcamento in self.orcamentos]
        if len(fornecedores) != len(set(fornecedores)):
            raise ValueError("Há dois orçamentos do mesmo fornecedor. Junte-os ou remova um.")

        solicitados = set(produtos)
        for orcamento in self.orcamentos:
            if any(item.produto_id not in solicitados for item in orcamento.itens):
                raise ValueError("Todo produto dos orçamentos precisa estar nos itens da solicitação.")

        return self
