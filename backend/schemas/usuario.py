from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UsuarioCriacao(BaseModel):
    nome: str = Field(min_length=2, max_length=150)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=72)


class UsuarioResposta(BaseModel):
    id: int
    nome: str
    email: EmailStr
    ativo: bool
    data_criacao: datetime

    model_config = ConfigDict(from_attributes=True)