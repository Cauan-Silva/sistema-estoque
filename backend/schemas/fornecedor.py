from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class FornecedorCriacao(BaseModel):
    nome: str = Field(
        min_length=2,
        max_length=150
    )
    cpf_cnpj: str | None = Field(
        default=None,
        max_length=20
    )
    contato: str | None = Field(
        default=None,
        max_length=150
    )
    telefone: str | None = Field(
        default=None,
        max_length=30
    )
    email: EmailStr | None = None
    site: str | None = Field(
        default=None,
        max_length=255
    )


class FornecedorAtualizacao(FornecedorCriacao):
    pass


class FornecedorStatus(BaseModel):
    ativo: bool


class FornecedorResposta(BaseModel):
    id: int
    nome: str
    cpf_cnpj: str | None
    contato: str | None
    telefone: str | None
    email: EmailStr | None
    site: str | None
    ativo: bool
    data_criacao: datetime