from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from backend.permissoes import exigir
from backend.repositorio_auditoria import listar_auditoria


router = APIRouter(
    prefix="/auditoria",
    tags=["Auditoria"],
    dependencies=[exigir("auditoria.ver")]
)


class RegistroAuditoria(BaseModel):
    id: int
    data_hora: datetime
    id_requisicao: str
    usuario_id: int | None
    usuario: str | None
    metodo: str
    caminho: str
    status: int
    ip: str | None
    duracao_ms: int


class PaginaAuditoria(BaseModel):
    total: int
    pagina: int
    tamanho: int
    itens: list[RegistroAuditoria]


@router.get("", response_model=PaginaAuditoria)
def listar(
    usuario_id: int | None = Query(default=None, gt=0),
    metodo: Literal["POST", "PUT", "PATCH", "DELETE"] | None = None,
    somente_falhas: bool = False,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    pagina: int = Query(default=1, ge=1),
    tamanho: int = Query(default=50, ge=1, le=200)
):
    resultado = listar_auditoria(
        usuario_id=usuario_id,
        metodo=metodo,
        somente_falhas=somente_falhas,
        data_inicio=data_inicio,
        data_fim=data_fim,
        pagina=pagina,
        tamanho=tamanho
    )

    if resultado is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível listar a auditoria."
        )

    return resultado
