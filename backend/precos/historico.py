import logging
from decimal import Decimal

import psycopg2

from backend.database import conectar


logger = logging.getLogger(__name__)


def _dinheiro(valor):
    return float(Decimal(valor).quantize(Decimal("0.01"))) if valor is not None else None


def historico_do_produto(produto_id: int, limite: int = 10):
    conexao = conectar()

    if conexao is None:
        return None

    try:
        cursor = conexao.cursor()

        cursor.execute(
            "SELECT id, nome, preco FROM produtos WHERE id = %s;",
            (produto_id,)
        )

        produto = cursor.fetchone()

        if produto is None:
            cursor.close()
            conexao.close()
            return {"produto": None}

        cursor.execute(
            """
            SELECT
                MIN(ic.preco_unitario),
                MAX(ic.preco_unitario),
                SUM(ic.subtotal) / NULLIF(SUM(ic.quantidade), 0),
                COUNT(*)
            FROM itens_compra ic
            WHERE ic.produto_id = %s;
            """,
            (produto_id,)
        )

        menor, maior, media, total_compras = cursor.fetchone()

        cursor.execute(
            """
            SELECT
                c.data_compra,
                f.nome,
                ic.quantidade,
                ic.preco_unitario,
                c.solicitacao_id
            FROM itens_compra ic
            JOIN compras c
                ON c.id = ic.compra_id
            JOIN fornecedores f
                ON f.id = c.fornecedor_id
            WHERE ic.produto_id = %s
            ORDER BY c.data_compra DESC, c.id DESC
            LIMIT %s;
            """,
            (produto_id, limite)
        )

        compras = [
            {
                "data": r[0],
                "fornecedor": r[1],
                "quantidade": r[2],
                "preco_unitario": _dinheiro(r[3]),
                "solicitacao_id": r[4],
            }
            for r in cursor.fetchall()
        ]

        cursor.execute(
            """
            SELECT
                ct.data_criacao,
                f.nome,
                ic.preco_unitario,
                ct.solicitacao_id
            FROM itens_cotacao ic
            JOIN cotacoes ct
                ON ct.id = ic.cotacao_id
            JOIN fornecedores f
                ON f.id = ct.fornecedor_id
            WHERE ic.produto_id = %s
            ORDER BY ct.data_criacao DESC, ct.id DESC
            LIMIT %s;
            """,
            (produto_id, limite)
        )

        cotacoes = [
            {
                "data": r[0],
                "fornecedor": r[1],
                "preco_unitario": _dinheiro(r[2]),
                "solicitacao_id": r[3],
            }
            for r in cursor.fetchall()
        ]

        cursor.close()
        conexao.close()

        return {
            "produto": {"id": produto[0], "nome": produto[1], "preco_cadastro": _dinheiro(produto[2])},
            "resumo": {
                "ultimo_pago": compras[0]["preco_unitario"] if compras else None,
                "menor_pago": _dinheiro(menor),
                "maior_pago": _dinheiro(maior),
                "media_paga": _dinheiro(media),
                "compras": total_compras,
            },
            "compras": compras,
            "cotacoes": cotacoes,
        }

    except psycopg2.Error as erro:
        conexao.close()
        logger.error("Erro ao consultar histórico de preços: %s", erro)
        return None
