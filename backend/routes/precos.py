from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from backend.autenticacao import obter_usuario_atual
from backend.precos.historico import historico_do_produto
from backend.precos.servico import consultar_fontes, fontes_disponiveis


router = APIRouter(
    prefix="/precos",
    tags=["Consulta de preços"],
    dependencies=[Depends(obter_usuario_atual)]
)


class ProdutoReferencia(BaseModel):
    id: int
    nome: str
    preco_cadastro: float


class ResumoHistorico(BaseModel):
    ultimo_pago: float | None
    menor_pago: float | None
    maior_pago: float | None
    media_paga: float | None
    compras: int


class CompraHistorico(BaseModel):
    data: date
    fornecedor: str
    quantidade: int
    preco_unitario: float
    solicitacao_id: int


class CotacaoHistorico(BaseModel):
    data: datetime
    fornecedor: str
    preco_unitario: float
    solicitacao_id: int


class OfertaResposta(BaseModel):
    titulo: str
    preco: float
    moeda: str
    link: str | None
    vendedor: str | None
    condicao: str | None


class ResumoOfertas(BaseModel):
    menor: float
    mediana: float
    maior: float
    quantidade: int


class FonteResposta(BaseModel):
    fonte: str
    situacao: str
    mensagem: str | None
    termo: str | None
    ofertas: list[OfertaResposta]
    resumo: ResumoOfertas | None


class ConsultaPrecosResposta(BaseModel):
    produto: ProdutoReferencia
    resumo: ResumoHistorico
    compras: list[CompraHistorico]
    cotacoes: list[CotacaoHistorico]
    externas: list[FonteResposta]


class FonteDisponivel(BaseModel):
    nome: str
    configurada: bool


@router.get("/fontes", response_model=list[FonteDisponivel])
def listar_fontes():
    return fontes_disponiveis()


@router.get("/produtos/{produto_id}", response_model=ConsultaPrecosResposta)
def consultar_produto(
    produto_id: int,
    busca: str | None = Query(default=None, min_length=2, max_length=120),
    externas: bool = True,
    limite: int = Query(default=10, ge=1, le=30)
):
    historico = historico_do_produto(produto_id, limite)

    if historico is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível consultar os preços."
        )

    if historico["produto"] is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado."
        )

    termo = (busca or historico["produto"]["nome"]).strip()

    return {
        **historico,
        "externas": consultar_fontes(termo, limite) if externas else [],
    }
