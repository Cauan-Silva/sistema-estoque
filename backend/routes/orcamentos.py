from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from backend.autenticacao import obter_usuario_atual
from backend.orcamentos.correspondencia import (
    sugerir_forma,
    sugerir_fornecedor,
    sugerir_produto,
)
from backend.orcamentos.leitura import (
    ErroLeitura,
    extrair,
    provedor_ia,
)
from backend.permissoes import exigir
from backend.repositorio import listar_produtos
from backend.repositorio_forma_pagamento import descrever, listar_formas_pagamento
from backend.repositorio_fornecedor import listar_fornecedores
from backend.repositorio_orcamento import (
    buscar_referencias,
    criar_solicitacao_com_cotacoes,
)
from backend.repositorio_solicitacao_compra import buscar_solicitacao
from backend.schemas.orcamento import SolicitacaoPorOrcamentos
from backend.schemas.solicitacao_compra import SolicitacaoCompraResposta


router = APIRouter(
    prefix="/orcamentos",
    tags=["Orçamentos"],
    dependencies=[Depends(obter_usuario_atual)]
)

TAMANHO_MAXIMO = 15 * 1024 * 1024

ERROS = {
    "produto_nao_encontrado": (status.HTTP_404_NOT_FOUND, "Um dos produtos não foi encontrado."),
    "fornecedor_nao_encontrado": (status.HTTP_404_NOT_FOUND, "Fornecedor não encontrado."),
    "fornecedor_inativo": (status.HTTP_400_BAD_REQUEST, "Um dos fornecedores está inativo."),
    "forma_pagamento_nao_encontrada": (status.HTTP_404_NOT_FOUND, "Forma de pagamento não encontrada."),
    "forma_pagamento_inativa": (status.HTTP_400_BAD_REQUEST, "Uma das formas de pagamento está inativa."),
}


def _fornecedores():
    return [
        {"id": f[0], "nome": f[1], "cpf_cnpj": f[2], "ativo": f[7]}
        for f in listar_fornecedores(ativo=True)
    ]


def _formas():
    resultado = listar_formas_pagamento(ativo=True, tamanho=1000)
    return resultado["itens"] if resultado else []


def _produtos():
    return [
        {"id": p.id, "nome": p.nome}
        for p in listar_produtos(pagina=1, tamanho=100000)
    ]


@router.get("/configuracao")
def configuracao():
    """Diz à tela se PDF e imagens podem ser lidos e por qual IA."""
    provedor = provedor_ia()
    return {"leitura_por_ia": provedor is not None, "provedor": provedor}


@router.post(
    "/ler",
    dependencies=[exigir("solicitacoes.editar"), exigir("cotacoes.editar")]
)
async def ler(arquivo: UploadFile = File(...)):
    """Lê um orçamento e sugere fornecedor, forma de pagamento e produtos. Não grava nada."""
    conteudo = await arquivo.read(TAMANHO_MAXIMO + 1)

    if not conteudo:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "O arquivo está vazio.")

    if len(conteudo) > TAMANHO_MAXIMO:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "O arquivo passa de 15 MB.")

    try:
        dados, origem = extrair(conteudo, arquivo.filename or "", arquivo.content_type)
    except ErroLeitura as erro:
        raise HTTPException(erro.status, str(erro))

    fornecedor = sugerir_fornecedor(dados["fornecedor_nome"], dados["fornecedor_cnpj"], _fornecedores())
    forma = sugerir_forma(dados["condicao_pagamento"], _formas())
    produtos = _produtos()
    referencias = buscar_referencias(fornecedor["id"]) if fornecedor else {}

    avisos = []
    if dados["tipo_documento"] == "nota_fiscal":
        avisos.append("Este arquivo é uma nota fiscal: os preços são de uma compra já feita.")
    if not dados["itens"]:
        avisos.append("Nenhum item foi encontrado no arquivo.")
    if not dados["fornecedor_nome"]:
        avisos.append("O fornecedor não aparece no arquivo. Escolha-o na revisão.")

    return {
        "arquivo": arquivo.filename,
        "origem": origem,
        **dados,
        "fornecedor_sugerido": {"id": fornecedor["id"], "nome": fornecedor["nome"]} if fornecedor else None,
        "forma_pagamento_sugerida": {"id": forma["id"], "descricao": descrever(forma)} if forma else None,
        "itens": [
            {**item, "produto_sugerido": sugerir_produto(item, produtos, referencias)}
            for item in dados["itens"]
        ],
        "avisos": avisos,
    }


@router.post(
    "/solicitacao",
    dependencies=[exigir("solicitacoes.editar"), exigir("cotacoes.editar")],
    response_model=SolicitacaoCompraResposta,
    status_code=status.HTTP_201_CREATED
)
def criar_solicitacao(
    dados: SolicitacaoPorOrcamentos,
    usuario=Depends(obter_usuario_atual)
):
    """Cria a solicitação com os itens revisados e uma cotação por orçamento."""
    solicitacao_id, erro = criar_solicitacao_com_cotacoes(
        solicitante_id=usuario[0],
        observacao=dados.observacao.strip() if dados.observacao else None,
        itens=[item.model_dump() for item in dados.itens],
        cotacoes=[orcamento.model_dump() for orcamento in dados.orcamentos],
    )

    if erro is not None or solicitacao_id is None:
        codigo, detalhe = ERROS.get(
            erro,
            (status.HTTP_500_INTERNAL_SERVER_ERROR, "Não foi possível criar a solicitação.")
        )
        raise HTTPException(codigo, detalhe)

    return buscar_solicitacao(solicitacao_id)
