from typing import Literal

from pydantic import BaseModel, Field, model_validator


TipoFormaPagamento = Literal["A_VISTA", "A_PRAZO"]


class FormaPagamentoEntrada(BaseModel):
    codigo: str = Field(
        min_length=1,
        max_length=10,
        pattern=r"^[0-9A-Za-z.\-]+$"
    )
    titulo: str = Field(
        min_length=2,
        max_length=100
    )
    tipo: TipoFormaPagamento
    parcelas: int = Field(
        default=1,
        ge=1,
        le=48
    )
    intervalo_dias: int = Field(
        default=0,
        ge=0,
        le=365
    )

    @model_validator(mode="after")
    def validar_a_vista(self):
        if self.tipo == "A_VISTA" and self.parcelas != 1:
            raise ValueError("Pagamento à vista deve ter uma única parcela.")

        return self


class FormaPagamentoStatus(BaseModel):
    ativo: bool


class FormaPagamentoResposta(BaseModel):
    id: int
    codigo: str
    titulo: str
    tipo: TipoFormaPagamento
    parcelas: int
    intervalo_dias: int
    ativo: bool


class FormasPagamentoPagina(BaseModel):
    total: int
    pagina: int
    tamanho: int
    itens: list[FormaPagamentoResposta]
