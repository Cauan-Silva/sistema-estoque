import logging
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

import psycopg2

from backend.database import conectar

logger = logging.getLogger(__name__)


CENTAVOS = Decimal("0.01")


def _dinheiro(valor) -> float:
    return float(
        Decimal(valor or 0).quantize(CENTAVOS, rounding=ROUND_HALF_UP)
    )


def _filtros(data_inicio, data_fim, fornecedor_id):
    condicoes = []
    parametros = []

    if data_inicio is not None:
        condicoes.append("c.data_compra >= %s")
        parametros.append(data_inicio)

    if data_fim is not None:
        condicoes.append("c.data_compra <= %s")
        parametros.append(data_fim)

    if fornecedor_id is not None:
        condicoes.append("c.fornecedor_id = %s")
        parametros.append(fornecedor_id)

    clausula = " WHERE " + " AND ".join(condicoes) if condicoes else ""

    return clausula, parametros


def gerar_relatorio_compras(
    data_inicio: date | None = None,
    data_fim: date | None = None,
    fornecedor_id: int | None = None
):
    conexao = conectar()

    if conexao is None:
        return None

    clausula, parametros = _filtros(data_inicio, data_fim, fornecedor_id)

    try:
        cursor = conexao.cursor()

        cursor.execute(
            f"""
            SELECT
                c.fornecedor_id,
                f.nome,
                c.data_compra,
                c.previsao_entrega,
                c.valor_total,
                c.valor_itens,
                c.frete,
                tc.comprado,
                tr.recebido,
                tr.ultimo_recebimento
            FROM compras c
            JOIN fornecedores f
                ON f.id = c.fornecedor_id
            LEFT JOIN LATERAL (
                SELECT COALESCE(SUM(ic.quantidade), 0) AS comprado
                FROM itens_compra ic
                WHERE ic.compra_id = c.id
            ) tc ON TRUE
            LEFT JOIN LATERAL (
                SELECT
                    COALESCE(SUM(ir.quantidade), 0) AS recebido,
                    MAX(r.data_recebimento) AS ultimo_recebimento
                FROM recebimentos r
                JOIN itens_recebimento ir
                    ON ir.recebimento_id = r.id
                WHERE r.compra_id = c.id
            ) tr ON TRUE
            {clausula}
            ORDER BY c.data_compra, c.id;
            """,
            tuple(parametros)
        )

        compras = cursor.fetchall()

        cursor.execute(
            f"""
            SELECT
                p.id,
                p.nome,
                SUM(ic.quantidade),
                SUM(ic.subtotal),
                MIN(ic.preco_unitario),
                MAX(ic.preco_unitario)
            FROM itens_compra ic
            JOIN compras c
                ON c.id = ic.compra_id
            JOIN produtos p
                ON p.id = ic.produto_id
            {clausula}
            GROUP BY p.id, p.nome
            ORDER BY SUM(ic.subtotal) DESC, p.nome;
            """,
            tuple(parametros)
        )

        produtos = cursor.fetchall()

        cursor.close()
        conexao.close()

    except psycopg2.Error as erro:
        conexao.close()

        logger.error(f"Erro ao gerar relatório de compras: {erro}")

        return None

    hoje = date.today()

    valor_total = Decimal("0")
    valor_itens = Decimal("0")
    frete_total = Decimal("0")

    completas = 0
    parciais = 0
    pendentes = 0
    no_prazo = 0
    atrasadas = 0
    atrasadas_em_aberto = 0
    dias_entrega = []

    por_fornecedor = {}
    por_mes = {}

    for (
        fornecedor_id_compra,
        fornecedor,
        data_compra,
        previsao,
        total,
        itens,
        frete,
        comprado,
        recebido,
        ultimo
    ) in compras:
        valor_total += total
        valor_itens += itens
        frete_total += frete

        fornecedor_resumo = por_fornecedor.setdefault(
            fornecedor_id_compra,
            {
                "fornecedor_id": fornecedor_id_compra,
                "fornecedor": fornecedor,
                "compras": 0,
                "valor_total": Decimal("0"),
                "entregas_no_prazo": 0,
                "entregas_atrasadas": 0
            }
        )

        fornecedor_resumo["compras"] += 1
        fornecedor_resumo["valor_total"] += total

        mes = data_compra.strftime("%Y-%m")
        mes_resumo = por_mes.setdefault(
            mes,
            {"mes": mes, "compras": 0, "valor_total": Decimal("0")}
        )
        mes_resumo["compras"] += 1
        mes_resumo["valor_total"] += total

        if recebido == 0:
            pendentes += 1
        elif recebido < comprado:
            parciais += 1
        else:
            completas += 1
            dias_entrega.append((ultimo - data_compra).days)

            if ultimo <= previsao:
                no_prazo += 1
                fornecedor_resumo["entregas_no_prazo"] += 1
            else:
                atrasadas += 1
                fornecedor_resumo["entregas_atrasadas"] += 1

        if recebido < comprado and previsao < hoje:
            atrasadas_em_aberto += 1

    total_compras = len(compras)

    return {
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "total_compras": total_compras,
        "valor_total": _dinheiro(valor_total),
        "valor_itens": _dinheiro(valor_itens),
        "frete_total": _dinheiro(frete_total),
        "ticket_medio": (
            _dinheiro(valor_total / total_compras)
            if total_compras
            else 0.0
        ),
        "compras_recebidas": completas,
        "compras_parciais": parciais,
        "compras_pendentes": pendentes,
        "entregas_no_prazo": no_prazo,
        "entregas_atrasadas": atrasadas,
        "percentual_no_prazo": (
            round(no_prazo * 100 / completas, 1)
            if completas
            else None
        ),
        "prazo_medio_entrega_dias": (
            round(sum(dias_entrega) / len(dias_entrega), 1)
            if dias_entrega
            else None
        ),
        "atrasadas_em_aberto": atrasadas_em_aberto,
        "por_fornecedor": sorted(
            (
                {**item, "valor_total": _dinheiro(item["valor_total"])}
                for item in por_fornecedor.values()
            ),
            key=lambda item: (-item["valor_total"], item["fornecedor"])
        ),
        "por_produto": [
            {
                "produto_id": registro[0],
                "produto": registro[1],
                "quantidade": int(registro[2]),
                "valor_total": _dinheiro(registro[3]),
                "preco_medio": _dinheiro(
                    Decimal(registro[3]) / int(registro[2])
                ),
                "menor_preco": _dinheiro(registro[4]),
                "maior_preco": _dinheiro(registro[5])
            }
            for registro in produtos
        ],
        "por_mes": [
            {**item, "valor_total": _dinheiro(item["valor_total"])}
            for item in sorted(por_mes.values(), key=lambda m: m["mes"])
        ],
    }
