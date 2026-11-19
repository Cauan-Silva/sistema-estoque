from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


Perfil = Literal[
    "ADMINISTRADOR",
    "COMPRADOR",
    "APROVADOR",
    "ALMOXARIFE",
    "CONSULTA",
]


class UsuarioCriacao(BaseModel):
    nome: str = Field(min_length=2, max_length=150)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=72)
    # Só vale quando um administrador cadastra; o primeiro usuário é sempre
    # ADMINISTRADOR e, sem perfil, o novo usuário entra como CONSULTA.
    perfil: Perfil | None = None


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


class UsuarioAcesso(BaseModel):
    perfil: Perfil | None = None
    ativo: bool | None = None


class ConfiguracaoInicialResposta(BaseModel):
    precisa_configurar: bool


class TokenResposta(BaseModel):
    access_token: str
    token_type: str