from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

from backend.autenticacao import obter_usuario_atual
from backend.permissoes import exigir
from backend.precos.historico import historico_do_produto
from backend.precos.referencias import (
    excluir_referencia,
    listar_referencias,
    registrar_referencia,
)
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


class ReferenciaResposta(BaseModel):
    id: int
    produto_id: int
    valor: float
    fonte: str
    link: str | None
    observacao: str | None
    usuario: str | None
    data_registro: datetime


class ReferenciaEntrada(BaseModel):
    valor: float = Field(ge=0)
    fonte: str = Field(default="Mercado Livre", min_length=2, max_length=60)
    link: str | None = Field(default=None, max_length=500)
    observacao: str | None = Field(default=None, max_length=300)

    @field_validator("link")
    @classmethod
    def link_web(cls, link):
        if link and not link.strip().lower().startswith(("http://", "https://")):
            raise ValueError("O link precisa começar com http:// ou https://.")
        return link.strip() if link else None


class ConsultaPrecosResposta(BaseModel):
    produto: ProdutoReferencia
    resumo: ResumoHistorico
    compras: list[CompraHistorico]
    cotacoes: list[CotacaoHistorico]
    referencias: list[ReferenciaResposta]
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
        "referencias": listar_referencias(produto_id, limite),
        "externas": consultar_fontes(termo, limite) if externas else [],
    }


@router.post(
    "/produtos/{produto_id}/referencias",
    dependencies=[exigir("solicitacoes.editar")],
    response_model=ReferenciaResposta,
    status_code=status.HTTP_201_CREATED
)
def anotar_referencia(
    produto_id: int,
    dados: ReferenciaEntrada,
    usuario=Depends(obter_usuario_atual)
):
    referencia, erro = registrar_referencia(
        produto_id=produto_id,
        valor=dados.valor,
        fonte=dados.fonte.strip(),
        link=dados.link,
        observacao=dados.observacao.strip() if dados.observacao else None,
        usuario_id=usuario[0],
    )

    if erro == "produto_nao_encontrado":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Produto não encontrado.")

    if erro or referencia is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Não foi possível salvar o preço de referência.")

    return referencia


@router.delete(
    "/referencias/{referencia_id}",
    dependencies=[exigir("solicitacoes.editar")],
    status_code=status.HTTP_204_NO_CONTENT
)
def remover_referencia(referencia_id: int):
    if not excluir_referencia(referencia_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Preço de referência não encontrado.")
