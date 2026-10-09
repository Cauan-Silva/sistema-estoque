from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from backend.autenticacao import obter_usuario_atual
from backend.repositorio_sugestao import sugestoes_de_compra


router = APIRouter(
    prefix="/sugestoes-compra",
    tags=["Sugestão de compra"],
    dependencies=[Depends(obter_usuario_atual)]
)


class Sugestao(BaseModel):
    produto_id: int
    produto: str
    categoria_id: int | None
    categoria: str | None
    estoque: int
    estoque_minimo: int
    em_pedido: int
    consumo_periodo: int
    consumo_mensal: float
    dias_restantes: int | None
    prazo_entrega_dias: int
    prazo_estimado: bool
    ponto_pedido: int
    sugerido: int
    motivo: str | None
    preco_referencia: float
    valor_estimado: float
    ultimo_fornecedor_id: int | None
    ultimo_fornecedor: str | None


@router.get("", response_model=list[Sugestao])
def sugerir(
    dias_consumo: int = Query(default=90, ge=7, le=730, description="Período usado para calcular o consumo médio."),
    cobertura_dias: int = Query(default=30, ge=0, le=365, description="Dias de consumo a cobrir depois da entrega."),
    prazo_padrao: int = Query(default=7, ge=0, le=180, description="Prazo de entrega usado quando o produto nunca foi comprado."),
    todos: bool = Query(default=False, description="Inclui produtos que não precisam de compra."),
):
    resultado = sugestoes_de_compra(dias_consumo, cobertura_dias, prazo_padrao, todos)

    if resultado is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Não foi possível calcular as sugestões.")

    return resultado
