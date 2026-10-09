from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.autenticacao import obter_usuario_atual
from backend.repositorio_notificacoes import notificacoes_do_usuario


router = APIRouter(prefix="/notificacoes", tags=["Notificações"])


class Notificacao(BaseModel):
    tipo: str
    titulo: str
    descricao: str
    link: str
    urgente: bool


class NotificacoesResposta(BaseModel):
    total: int
    itens: list[Notificacao]


@router.get("", response_model=NotificacoesResposta)
def listar(usuario=Depends(obter_usuario_atual)):
    """O que este usuário precisa fazer agora, conforme o perfil dele."""
    resultado = notificacoes_do_usuario(usuario)

    if resultado is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Não foi possível carregar as notificações.")

    return resultado
