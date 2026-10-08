from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UsuarioCriacao(BaseModel):
    nome: str = Field(min_length=2, max_length=150)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=72)


class UsuarioLogin(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=8, max_length=72)


class UsuarioResposta(BaseModel):
    id: int
    nome: str
    email: EmailStr
    ativo: bool
    data_criacao: datetime
    perfil: str = "CONSULTA"

    model_config = ConfigDict(from_attributes=True)


class UsuarioAtualResposta(UsuarioResposta):
    permissoes: list[str]


Perfil = Literal[
    "ADMINISTRADOR",
    "COMPRADOR",
    "APROVADOR",
    "ALMOXARIFE",
    "CONSULTA",
]


class UsuarioAcesso(BaseModel):
    perfil: Perfil | None = None
    ativo: bool | None = None


class TokenResposta(BaseModel):
    access_token: str
    token_type: str