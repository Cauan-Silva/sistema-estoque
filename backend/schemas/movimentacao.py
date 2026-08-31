from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class MovimentacaoCriar(BaseModel):
    produto_id: int = Field(gt=0)
    tipo: Literal["ENTRADA", "SAIDA"]
    quantidade: int = Field(gt=0)


class MovimentacaoResposta(BaseModel):
    id: int
    produto_id: int
    produto_nome: str
    tipo: str
    quantidade: int
    data_movimentacao: datetime