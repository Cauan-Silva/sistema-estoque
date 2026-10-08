from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response

from backend.autenticacao import obter_usuario_atual
from backend.exportacao import Tabela, gerar_pdf, gerar_xlsx
from backend.repositorio import listar_produtos
from backend.repositorio_compra import listar_compras
from backend.repositorio_fornecedor import listar_fornecedores
from backend.repositorio_movimentacao import listar_movimentacoes
from backend.repositorio_relatorio_compras import gerar_relatorio_compras


router = APIRouter(
    prefix="/exportacoes",
    tags=["Exportações"],
    dependencies=[Depends(obter_usuario_atual)]
)

Formato = Literal["xlsx", "pdf"]

LIMITE = 100000

TIPOS_ARQUIVO = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}

NOMES_SITUACAO = {
    "PENDENTE": "Pendente",
    "PARCIAL": "Parcial",
    "COMPLETO": "Completa",
}


def _validar_periodo(data_inicio, data_fim):
    if data_inicio and data_fim and data_inicio > data_fim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A data inicial não pode ser posterior à data final."
        )


def _descrever_periodo(data_inicio, data_fim) -> str:
    if data_inicio and data_fim:
        return f"de {data_inicio:%d/%m/%Y} a {data_fim:%d/%m/%Y}"
    if data_inicio:
        return f"a partir de {data_inicio:%d/%m/%Y}"
    if data_fim:
        return f"até {data_fim:%d/%m/%Y}"
    return "todo o período"


def _arquivo(nome: str, formato: str, titulo: str, subtitulo: str, tabelas: list[Tabela]):
    gerado_em = datetime.now().strftime("%d/%m/%Y %H:%M")
    subtitulo_completo = f"{subtitulo}. Gerado em {gerado_em}." if subtitulo else f"Gerado em {gerado_em}."

    conteudo = (
        gerar_xlsx(tabelas)
        if formato == "xlsx"
        else gerar_pdf(titulo, subtitulo_completo, tabelas)
    )

    nome_arquivo = f"{nome}-{date.today():%Y-%m-%d}.{formato}"

    return Response(
        content=conteudo,
        media_type=TIPOS_ARQUIVO[formato],
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'}
    )


@router.get("/produtos")
def exportar_produtos(
    formato: Formato = "xlsx",
    busca: str | None = None,
    categoria_id: int | None = Query(default=None, gt=0),
    fornecedor_id: int | None = Query(default=None, gt=0),
    estoque_baixo: bool = False,
    limite_estoque: int = Query(default=5, ge=0)
):
    produtos = listar_produtos(
        busca=busca,
        categoria_id=categoria_id,
        fornecedor_id=fornecedor_id,
        estoque_baixo=estoque_baixo,
        limite_estoque=limite_estoque,
        pagina=1,
        tamanho=LIMITE
    )

    linhas = [
        [
            p.id,
            p.nome,
            p.categoria,
            p.fornecedor or "",
            p.quantidade,
            p.preco,
            round(p.quantidade * p.preco, 2),
        ]
        for p in produtos
    ]

    tabela = Tabela(
        titulo="Produtos",
        colunas=[
            ("Código", "inteiro", 9),
            ("Produto", "texto", 40),
            ("Categoria", "texto", 22),
            ("Fornecedor", "texto", 26),
            ("Quantidade", "inteiro", 13),
            ("Preço", "moeda", 14),
            ("Valor em estoque", "moeda", 18),
        ],
        linhas=linhas,
        totais=[
            None,
            "Total",
            None,
            None,
            sum(l[4] for l in linhas),
            None,
            round(sum(l[6] for l in linhas), 2),
        ] if linhas else None,
    )

    filtro = "Somente estoque baixo" if estoque_baixo else f"{len(linhas)} produtos"

    return _arquivo("produtos", formato, "Produtos em estoque", filtro, [tabela])


@router.get("/movimentacoes")
def exportar_movimentacoes(
    formato: Formato = "xlsx",
    produto_id: int | None = Query(default=None, gt=0),
    tipo: Literal["ENTRADA", "SAIDA"] | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None
):
    _validar_periodo(data_inicio, data_fim)

    movimentacoes = listar_movimentacoes(
        produto_id=produto_id,
        tipo=tipo,
        data_inicio=datetime.combine(data_inicio, datetime.min.time()) if data_inicio else None,
        data_fim=datetime.combine(data_fim, datetime.max.time()) if data_fim else None,
        pagina=1,
        tamanho=LIMITE
    )

    tabela = Tabela(
        titulo="Movimentações",
        colunas=[
            ("Data", "data", 18),
            ("Produto", "texto", 42),
            ("Tipo", "texto", 12),
            ("Quantidade", "inteiro", 13),
            ("Origem", "texto", 22),
        ],
        linhas=[
            [
                m["data_movimentacao"],
                m["produto_nome"],
                "Entrada" if m["tipo"] == "ENTRADA" else "Saída",
                m["quantidade"],
                f"Recebimento Nº {m['recebimento_id']}" if m.get("recebimento_id") else "Manual",
            ]
            for m in movimentacoes
        ],
    )

    return _arquivo(
        "movimentacoes",
        formato,
        "Movimentações de estoque",
        f"Período: {_descrever_periodo(data_inicio, data_fim)}",
        [tabela],
    )


@router.get("/fornecedores")
def exportar_fornecedores(
    formato: Formato = "xlsx",
    ativo: bool | None = None
):
    fornecedores = listar_fornecedores(ativo=ativo)

    tabela = Tabela(
        titulo="Fornecedores",
        colunas=[
            ("Fornecedor", "texto", 34),
            ("CPF ou CNPJ", "texto", 18),
            ("Contato", "texto", 22),
            ("Telefone", "texto", 16),
            ("E-mail", "texto", 30),
            ("Site", "texto", 26),
            ("Situação", "texto", 11),
        ],
        linhas=[
            [f[1], f[2] or "", f[3] or "", f[4] or "", f[5] or "", f[6] or "", "Ativo" if f[7] else "Inativo"]
            for f in fornecedores
        ],
    )

    return _arquivo("fornecedores", formato, "Fornecedores", f"{len(fornecedores)} fornecedores", [tabela])


@router.get("/compras")
def exportar_compras(
    formato: Formato = "xlsx",
    fornecedor_id: int | None = Query(default=None, gt=0),
    situacao_recebimento: Literal["PENDENTE", "PARCIAL", "COMPLETO"] | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None
):
    _validar_periodo(data_inicio, data_fim)

    compras = listar_compras(
        fornecedor_id=fornecedor_id,
        situacao_recebimento=situacao_recebimento,
        data_inicio=data_inicio,
        data_fim=data_fim,
        pagina=1,
        tamanho=LIMITE
    )

    tabela = Tabela(
        titulo="Compras",
        colunas=[
            ("Data", "data", 12),
            ("Pedido", "texto", 14),
            ("Solicitação", "inteiro", 11),
            ("Fornecedor", "texto", 30),
            ("Pagamento", "texto", 22),
            ("Previsão", "data", 12),
            ("Entrega", "texto", 11),
            ("Frete", "moeda", 12),
            ("Total", "moeda", 14),
        ],
        linhas=[
            [
                c["data_compra"],
                c["numero_pedido"] or "",
                c["solicitacao_id"],
                c["fornecedor"],
                c.get("forma_pagamento") or "",
                c["previsao_entrega"],
                NOMES_SITUACAO[c["situacao_recebimento"]],
                c["frete"],
                c["valor_total"],
            ]
            for c in compras
        ],
    )

    if tabela.linhas:
        tabela.totais = [None, "Total", None, None, None, None, None,
                         round(sum(c["frete"] for c in compras), 2),
                         round(sum(c["valor_total"] for c in compras), 2)]

    return _arquivo(
        "compras",
        formato,
        "Compras",
        f"Período: {_descrever_periodo(data_inicio, data_fim)}",
        [tabela],
    )


@router.get("/relatorio-compras")
def exportar_relatorio_compras(
    formato: Formato = "xlsx",
    data_inicio: date | None = None,
    data_fim: date | None = None,
    fornecedor_id: int | None = Query(default=None, gt=0)
):
    _validar_periodo(data_inicio, data_fim)

    dados = gerar_relatorio_compras(
        data_inicio=data_inicio,
        data_fim=data_fim,
        fornecedor_id=fornecedor_id
    )

    if dados is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível gerar o relatório de compras."
        )

    no_prazo = (
        f"{dados['percentual_no_prazo']}%".replace(".", ",")
        if dados["percentual_no_prazo"] is not None
        else "-"
    )
    prazo_medio = (
        f"{dados['prazo_medio_entrega_dias']} dias".replace(".", ",")
        if dados["prazo_medio_entrega_dias"] is not None
        else "-"
    )

    tabelas = [
        Tabela(
            titulo="Resumo",
            colunas=[("Indicador", "texto", 36), ("Valor", "texto", 24)],
            linhas=[
                ["Compras", str(dados["total_compras"])],
                ["Valor comprado", f"R$ {dados['valor_total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")],
                ["Valor médio por compra", f"R$ {dados['ticket_medio']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")],
                ["Frete pago", f"R$ {dados['frete_total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")],
                ["Entregas completas", str(dados["compras_recebidas"])],
                ["Entregas parciais", str(dados["compras_parciais"])],
                ["Entregas pendentes", str(dados["compras_pendentes"])],
                ["Entregas no prazo", no_prazo],
                ["Tempo médio de entrega", prazo_medio],
                ["Atrasadas sem entrega", str(dados["atrasadas_em_aberto"])],
            ],
        ),
        Tabela(
            titulo="Por mês",
            colunas=[("Mês", "texto", 14), ("Compras", "inteiro", 12), ("Valor", "moeda", 16)],
            linhas=[[m["mes"], m["compras"], m["valor_total"]] for m in dados["por_mes"]],
        ),
        Tabela(
            titulo="Por fornecedor",
            colunas=[
                ("Fornecedor", "texto", 36),
                ("Compras", "inteiro", 12),
                ("Valor", "moeda", 16),
                ("No prazo", "inteiro", 12),
                ("Com atraso", "inteiro", 12),
            ],
            linhas=[
                [f["fornecedor"], f["compras"], f["valor_total"], f["entregas_no_prazo"], f["entregas_atrasadas"]]
                for f in dados["por_fornecedor"]
            ],
        ),
        Tabela(
            titulo="Por produto",
            colunas=[
                ("Produto", "texto", 36),
                ("Quantidade", "inteiro", 12),
                ("Valor", "moeda", 16),
                ("Preço médio", "moeda", 14),
                ("Menor preço", "moeda", 14),
                ("Maior preço", "moeda", 14),
            ],
            linhas=[
                [p["produto"], p["quantidade"], p["valor_total"], p["preco_medio"], p["menor_preco"], p["maior_preco"]]
                for p in dados["por_produto"]
            ],
        ),
    ]

    return _arquivo(
        "relatorio-compras",
        formato,
        "Relatório de compras",
        f"Período: {_descrever_periodo(data_inicio, data_fim)}",
        tabelas,
    )
