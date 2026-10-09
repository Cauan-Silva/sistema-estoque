import re
import unicodedata
from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import Response

from backend.autenticacao import obter_usuario_atual
from backend.exportacao import Tabela
from backend.permissoes import exigir
from backend.planilha_orcamento import (
    PlanilhaInvalida,
    encontrar_forma,
    encontrar_fornecedor,
    gerar_modelo,
    ler_planilha,
)
from backend.repositorio_forma_pagamento import listar_formas_pagamento
from backend.repositorio_fornecedor import listar_fornecedores
from backend.repositorio_solicitacao_compra import buscar_solicitacao
from backend.routes.exportacoes import _arquivo
from backend.repositorio_cotacao import (
    atualizar_cotacao,
    buscar_cotacao,
    comparar_cotacoes,
    criar_cotacao,
    excluir_cotacao,
    listar_cotacoes,
)
from backend.schemas.cotacao import (
    ComparacaoCotacoesResposta,
    CotacaoAtualizacao,
    CotacaoCriacao,
    CotacaoResposta,
)


router = APIRouter(
    prefix="/solicitacoes-compra/{solicitacao_id}/cotacoes",
    tags=["Cotações"],
    dependencies=[
        Depends(obter_usuario_atual)
    ]
)


ERROS = {
    "solicitacao_nao_encontrada": (
        status.HTTP_404_NOT_FOUND,
        "Solicitação de compra não encontrada."
    ),
    "cotacao_nao_encontrada": (
        status.HTTP_404_NOT_FOUND,
        "Cotação não encontrada."
    ),
    "fornecedor_nao_encontrado": (
        status.HTTP_404_NOT_FOUND,
        "Fornecedor não encontrado."
    ),
    "fornecedor_inativo": (
        status.HTTP_400_BAD_REQUEST,
        "Fornecedor inativo."
    ),
    "forma_pagamento_nao_encontrada": (
        status.HTTP_404_NOT_FOUND,
        "Forma de pagamento não encontrada."
    ),
    "forma_pagamento_inativa": (
        status.HTTP_400_BAD_REQUEST,
        "Forma de pagamento inativa."
    ),
    "produto_fora_da_solicitacao": (
        status.HTTP_400_BAD_REQUEST,
        "A cotação só pode conter produtos da solicitação."
    ),
    "cotacao_duplicada": (
        status.HTTP_409_CONFLICT,
        "Este fornecedor já possui cotação para esta solicitação."
    ),
    "solicitacao_nao_permite_cotacao": (
        status.HTTP_409_CONFLICT,
        "A solicitação não permite alterar cotações no status atual."
    ),
}


def tratar_erro(erro: str | None, mensagem_padrao: str):
    codigo, detalhe = ERROS.get(
        erro,
        (
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            mensagem_padrao
        )
    )

    raise HTTPException(
        status_code=codigo,
        detail=detalhe
    )


def itens_para_dict(itens):
    return [
        {
            "produto_id": item.produto_id,
            "preco_unitario": item.preco_unitario
        }
        for item in itens
    ]


@router.post(
    "",
    dependencies=[exigir("cotacoes.editar")],
    response_model=CotacaoResposta,
    status_code=status.HTTP_201_CREATED
)
def criar(solicitacao_id: int, dados: CotacaoCriacao):
    cotacao, erro = criar_cotacao(
        solicitacao_id=solicitacao_id,
        fornecedor_id=dados.fornecedor_id,
        frete=dados.frete,
        prazo_entrega_dias=dados.prazo_entrega_dias,
        validade=dados.validade,
        observacao=dados.observacao,
        itens=itens_para_dict(dados.itens),
        forma_pagamento_id=dados.forma_pagamento_id
    )

    if erro is not None or cotacao is None:
        tratar_erro(erro, "Não foi possível registrar a cotação.")

    return cotacao


@router.get(
    "",
    response_model=list[CotacaoResposta]
)
def listar(solicitacao_id: int):
    cotacoes = listar_cotacoes(solicitacao_id)

    if cotacoes is None:
        tratar_erro("solicitacao_nao_encontrada", "")

    return cotacoes


@router.get(
    "/comparacao",
    response_model=ComparacaoCotacoesResposta
)
def comparar(solicitacao_id: int):
    comparacao = comparar_cotacoes(solicitacao_id)

    if comparacao is None:
        tratar_erro("solicitacao_nao_encontrada", "")

    return comparacao


# ---------- Planilha de orçamento: modelo, importação e exportação ----------

TIPO_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
TAMANHO_MAXIMO_PLANILHA = 5 * 1024 * 1024


def _fornecedores(ativo=None):
    return [
        {"id": f[0], "nome": f[1], "cpf_cnpj": f[2], "ativo": f[7]}
        for f in listar_fornecedores(ativo=ativo)
    ]


def _formas(ativo=None):
    resultado = listar_formas_pagamento(ativo=ativo, tamanho=1000)
    return resultado["itens"] if resultado else []


def _solicitacao_ou_404(solicitacao_id: int):
    solicitacao = buscar_solicitacao(solicitacao_id)

    if solicitacao is None:
        tratar_erro("solicitacao_nao_encontrada", "")

    return solicitacao


def _planilha(conteudo: bytes, nome: str):
    return Response(
        content=conteudo,
        media_type=TIPO_XLSX,
        headers={"Content-Disposition": f'attachment; filename="{nome}"'}
    )


def _erro_planilha(mensagem: str, codigo=status.HTTP_400_BAD_REQUEST):
    raise HTTPException(status_code=codigo, detail=mensagem)


@router.get("/modelo")
def baixar_modelo(solicitacao_id: int):
    """Modelo padrão de orçamento, já com os itens da solicitação."""
    solicitacao = _solicitacao_ou_404(solicitacao_id)

    conteudo = gerar_modelo(solicitacao, _fornecedores(ativo=True), _formas(ativo=True))

    return _planilha(conteudo, f"orcamento-solicitacao-{solicitacao_id}.xlsx")


@router.get("/exportar")
def exportar(solicitacao_id: int, formato: Literal["xlsx", "pdf"] = "xlsx"):
    """Todas as cotações da solicitação: resumo e preço de cada item por fornecedor."""
    solicitacao = _solicitacao_ou_404(solicitacao_id)
    cotacoes = listar_cotacoes(solicitacao_id) or []
    total_itens = len(solicitacao["itens"])

    resumo = Tabela(
        titulo="Cotações",
        colunas=[
            ("Fornecedor", "texto", 30),
            ("Forma de pagamento", "texto", 26),
            ("Prazo (dias)", "inteiro", 12),
            ("Validade", "data", 12),
            ("Itens cotados", "texto", 13),
            ("Valor dos itens", "moeda", 16),
            ("Frete", "moeda", 12),
            ("Total", "moeda", 16),
        ],
        linhas=[
            [
                c["fornecedor"],
                c.get("forma_pagamento") or "",
                c["prazo_entrega_dias"],
                c["validade"],
                f"{len(c['itens'])} de {total_itens}",
                c["valor_itens"],
                c["frete"],
                c["valor_total"],
            ]
            for c in sorted(cotacoes, key=lambda c: c["valor_total"])
        ],
    )

    precos = {
        c["id"]: {item["produto_id"]: item["preco_unitario"] for item in c["itens"]}
        for c in cotacoes
    }

    por_item = Tabela(
        titulo="Preço por item",
        colunas=[("Produto", "texto", 32), ("Quantidade", "inteiro", 12)]
        + [(c["fornecedor"][:24], "moeda", 16) for c in cotacoes],
        linhas=[
            [item["produto"], item["quantidade"]]
            + [precos[c["id"]].get(item["produto_id"]) for c in cotacoes]
            for item in solicitacao["itens"]
        ],
        observacao="Preço unitário oferecido por cada fornecedor. Vazio: item sem oferta.",
    )

    return _arquivo(
        f"cotacoes-solicitacao-{solicitacao_id}",
        formato,
        f"Cotações da solicitação Nº {solicitacao_id}",
        f"{len(cotacoes)} cotação(ões) para {total_itens} item(ns)",
        [resumo, por_item],
    )


@router.post(
    "/importar",
    dependencies=[exigir("cotacoes.editar")],
    response_model=CotacaoResposta,
    status_code=status.HTTP_201_CREATED
)
async def importar(
    solicitacao_id: int,
    arquivo: UploadFile = File(...),
    substituir: bool = Query(
        default=False,
        description="Se o fornecedor já tiver cotação, atualiza a existente."
    )
):
    _solicitacao_ou_404(solicitacao_id)

    conteudo = await arquivo.read(TAMANHO_MAXIMO_PLANILHA + 1)

    if len(conteudo) > TAMANHO_MAXIMO_PLANILHA:
        _erro_planilha("A planilha passa de 5 MB.", status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

    try:
        dados = ler_planilha(conteudo)
    except PlanilhaInvalida as erro:
        _erro_planilha(str(erro))

    numero = dados["solicitacao"]
    if numero not in (None, "") and str(numero).strip() != str(solicitacao_id):
        _erro_planilha(
            f"Esta planilha é da solicitação Nº {numero}, não da Nº {solicitacao_id}."
        )

    if not dados["fornecedor"]:
        _erro_planilha("Informe o fornecedor na planilha.")

    fornecedor = encontrar_fornecedor(dados["fornecedor"], _fornecedores())

    if fornecedor is None:
        _erro_planilha(
            f"Fornecedor \"{dados['fornecedor']}\" não encontrado. Cadastre-o ou use o nome igual ao do sistema.",
            status.HTTP_404_NOT_FOUND
        )

    forma_pagamento_id = None
    if dados["forma_pagamento"]:
        forma = encontrar_forma(dados["forma_pagamento"], _formas())
        if forma is None:
            _erro_planilha(f"Forma de pagamento \"{dados['forma_pagamento']}\" não encontrada.")
        forma_pagamento_id = forma["id"]

    if dados["prazo"] is None:
        _erro_planilha("Informe o prazo de entrega em dias.")

    if not dados["itens"]:
        _erro_planilha("Preencha o preço unitário de pelo menos um item.")

    campos = {
        "frete": dados["frete"],
        "prazo_entrega_dias": dados["prazo"],
        "validade": dados["validade"],
        "observacao": dados["observacao"],
        "itens": dados["itens"],
        "forma_pagamento_id": forma_pagamento_id,
    }

    cotacao, erro = criar_cotacao(
        solicitacao_id=solicitacao_id,
        fornecedor_id=fornecedor["id"],
        **campos
    )

    if erro == "cotacao_duplicada" and substituir:
        existente = next(
            c for c in listar_cotacoes(solicitacao_id) or []
            if c["fornecedor_id"] == fornecedor["id"]
        )
        cotacao, erro = atualizar_cotacao(
            solicitacao_id=solicitacao_id,
            cotacao_id=existente["id"],
            **campos
        )

    if erro is not None or cotacao is None:
        tratar_erro(erro, "Não foi possível importar a cotação.")

    return cotacao


@router.get("/{cotacao_id}/planilha")
def baixar_planilha(solicitacao_id: int, cotacao_id: int):
    """A cotação no formato do modelo, para conferir ou reenviar ao fornecedor."""
    solicitacao = _solicitacao_ou_404(solicitacao_id)
    cotacao = buscar_cotacao(solicitacao_id, cotacao_id)

    if cotacao is None:
        tratar_erro("cotacao_nao_encontrada", "")

    conteudo = gerar_modelo(solicitacao, _fornecedores(ativo=True), _formas(ativo=True), cotacao)
    nome = unicodedata.normalize("NFKD", cotacao["fornecedor"]).encode("ascii", "ignore").decode()
    nome = re.sub(r"[^a-z0-9]+", "-", nome.lower()).strip("-")[:30] or "fornecedor"

    return _planilha(conteudo, f"orcamento-{solicitacao_id}-{nome}.xlsx")


@router.get(
    "/{cotacao_id}",
    response_model=CotacaoResposta
)
def buscar(solicitacao_id: int, cotacao_id: int):
    cotacao = buscar_cotacao(solicitacao_id, cotacao_id)

    if cotacao is None:
        tratar_erro("cotacao_nao_encontrada", "")

    return cotacao


@router.put(
    "/{cotacao_id}",
    dependencies=[exigir("cotacoes.editar")],
    response_model=CotacaoResposta
)
def editar(
    solicitacao_id: int,
    cotacao_id: int,
    dados: CotacaoAtualizacao
):
    cotacao, erro = atualizar_cotacao(
        solicitacao_id=solicitacao_id,
        cotacao_id=cotacao_id,
        frete=dados.frete,
        prazo_entrega_dias=dados.prazo_entrega_dias,
        validade=dados.validade,
        observacao=dados.observacao,
        itens=itens_para_dict(dados.itens),
        forma_pagamento_id=dados.forma_pagamento_id
    )

    if erro is not None or cotacao is None:
        tratar_erro(erro, "Não foi possível atualizar a cotação.")

    return cotacao


@router.delete(
    "/{cotacao_id}",
    dependencies=[exigir("cotacoes.editar")],
    status_code=status.HTTP_204_NO_CONTENT
)
def remover(solicitacao_id: int, cotacao_id: int):
    erro = excluir_cotacao(solicitacao_id, cotacao_id)

    if erro is not None:
        tratar_erro(erro, "Não foi possível excluir a cotação.")

    return None
