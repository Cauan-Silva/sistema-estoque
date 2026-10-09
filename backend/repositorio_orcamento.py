"""Cria uma solicitação de compra já com as cotações vindas de orçamentos.

Tudo numa transação só: se uma cotação falhar, nada é gravado.
"""

import logging

import psycopg2

from backend.database import conectar
from backend.orcamentos.correspondencia import chaves_do_item
from backend.repositorio_cotacao import (
    _validar_forma_pagamento,
    _validar_fornecedor,
)
from backend.repositorio_solicitacao_compra import (
    _inserir_itens as inserir_itens_solicitacao,
    _produtos_inexistentes,
)

logger = logging.getLogger(__name__)


def buscar_referencias(fornecedor_id: int) -> dict[str, int]:
    conexao = conectar()

    if conexao is None:
        return {}

    try:
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT chave, produto_id FROM referencias_fornecedor WHERE fornecedor_id = %s;",
            (fornecedor_id,)
        )
        referencias = dict(cursor.fetchall())
        cursor.close()
        conexao.close()
        return referencias

    except psycopg2.Error as erro:
        conexao.close()
        logger.error(f"Erro ao buscar referências do fornecedor: {erro}")
        return {}


def _salvar_referencias(cursor, fornecedor_id: int, itens):
    for item in itens:
        for chave in chaves_do_item({
            "codigo": item.get("codigo_fornecedor"),
            "descricao": item.get("descricao_fornecedor"),
        }):
            cursor.execute(
                """
                INSERT INTO referencias_fornecedor (fornecedor_id, chave, produto_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (fornecedor_id, chave)
                DO UPDATE SET produto_id = EXCLUDED.produto_id, atualizado_em = CURRENT_TIMESTAMP;
                """,
                (fornecedor_id, chave, item["produto_id"])
            )


def criar_solicitacao_com_cotacoes(
    solicitante_id: int,
    observacao: str | None,
    itens,
    cotacoes
):
    conexao = conectar()

    if conexao is None:
        return None, "erro_conexao"

    try:
        cursor = conexao.cursor()

        produto_ids = [item["produto_id"] for item in itens]
        if _produtos_inexistentes(cursor, produto_ids):
            conexao.rollback()
            conexao.close()
            return None, "produto_nao_encontrado"

        for cotacao in cotacoes:
            erro = (
                _validar_fornecedor(cursor, cotacao["fornecedor_id"])
                or _validar_forma_pagamento(cursor, cotacao.get("forma_pagamento_id"))
            )
            if erro:
                conexao.rollback()
                conexao.close()
                return None, erro

        cursor.execute(
            """
            INSERT INTO solicitacoes_compra (solicitante_id, observacao, status)
            VALUES (%s, %s, %s)
            RETURNING id;
            """,
            (solicitante_id, observacao, "EM_COTACAO" if cotacoes else "ABERTA")
        )
        solicitacao_id = cursor.fetchone()[0]

        inserir_itens_solicitacao(cursor, solicitacao_id, itens)

        for cotacao in cotacoes:
            cursor.execute(
                """
                INSERT INTO cotacoes (
                    solicitacao_id,
                    fornecedor_id,
                    frete,
                    prazo_entrega_dias,
                    validade,
                    observacao,
                    forma_pagamento_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    solicitacao_id,
                    cotacao["fornecedor_id"],
                    cotacao["frete"],
                    cotacao["prazo_entrega_dias"],
                    cotacao.get("validade"),
                    cotacao.get("observacao"),
                    cotacao.get("forma_pagamento_id"),
                )
            )
            cotacao_id = cursor.fetchone()[0]

            for item in cotacao["itens"]:
                cursor.execute(
                    """
                    INSERT INTO itens_cotacao (cotacao_id, produto_id, preco_unitario)
                    VALUES (%s, %s, %s);
                    """,
                    (cotacao_id, item["produto_id"], item["preco_unitario"])
                )

            _salvar_referencias(cursor, cotacao["fornecedor_id"], cotacao["itens"])

        conexao.commit()
        cursor.close()
        conexao.close()

        return solicitacao_id, None

    except psycopg2.Error as erro:
        conexao.rollback()
        conexao.close()

        logger.error(f"Erro ao criar solicitação a partir de orçamentos: {erro}")

        return None, "erro_banco"
