import logging
from datetime import date

import psycopg2

from backend.database import conectar

logger = logging.getLogger(__name__)


def _pendentes_por_produto(cursor, compra_id: int):
    cursor.execute(
        """
        SELECT
            ic.produto_id,
            ic.quantidade - COALESCE((
                SELECT SUM(ir.quantidade)
                FROM itens_recebimento ir
                JOIN recebimentos r
                    ON r.id = ir.recebimento_id
                WHERE r.compra_id = ic.compra_id
                  AND ir.produto_id = ic.produto_id
            ), 0)
        FROM itens_compra ic
        WHERE ic.compra_id = %s
        ORDER BY ic.id;
        """,
        (compra_id,)
    )

    return {
        registro[0]: int(registro[1])
        for registro in cursor.fetchall()
    }


def _buscar_itens(cursor, recebimento_id: int):
    cursor.execute(
        """
        SELECT
            ir.produto_id,
            p.nome,
            ir.quantidade,
            ir.movimentacao_id
        FROM itens_recebimento ir
        JOIN produtos p
            ON p.id = ir.produto_id
        WHERE ir.recebimento_id = %s
        ORDER BY ir.id;
        """,
        (recebimento_id,)
    )

    return [
        {
            "produto_id": registro[0],
            "produto": registro[1],
            "quantidade": registro[2],
            "movimentacao_id": registro[3]
        }
        for registro in cursor.fetchall()
    ]


CONSULTA_RECEBIMENTO = """
    SELECT
        r.id,
        r.compra_id,
        c.solicitacao_id,
        r.recebedor_id,
        u.nome,
        r.data_recebimento,
        r.nota_fiscal,
        r.observacao,
        r.data_criacao
    FROM recebimentos r
    JOIN compras c
        ON c.id = r.compra_id
    JOIN usuarios u
        ON u.id = r.recebedor_id
"""


def _montar_recebimento(cursor, registro):
    return {
        "id": registro[0],
        "compra_id": registro[1],
        "solicitacao_id": registro[2],
        "recebedor_id": registro[3],
        "recebedor": registro[4],
        "data_recebimento": registro[5],
        "nota_fiscal": registro[6],
        "observacao": registro[7],
        "data_criacao": registro[8],
        "itens": _buscar_itens(cursor, registro[0])
    }


def buscar_recebimento(recebimento_id: int):
    conexao = conectar()

    if conexao is None:
        return None

    try:
        cursor = conexao.cursor()

        cursor.execute(
            CONSULTA_RECEBIMENTO + " WHERE r.id = %s;",
            (recebimento_id,)
        )

        registro = cursor.fetchone()

        recebimento = (
            _montar_recebimento(cursor, registro)
            if registro is not None
            else None
        )

        cursor.close()
        conexao.close()

        return recebimento

    except psycopg2.Error as erro:
        conexao.close()

        logger.error(f"Erro ao buscar recebimento: {erro}")

        return None


def listar_recebimentos(solicitacao_id: int):
    conexao = conectar()

    if conexao is None:
        return None

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            SELECT 1
            FROM compras
            WHERE solicitacao_id = %s;
            """,
            (solicitacao_id,)
        )

        if cursor.fetchone() is None:
            cursor.close()
            conexao.close()

            return None

        cursor.execute(
            CONSULTA_RECEBIMENTO
            + " WHERE c.solicitacao_id = %s"
            + " ORDER BY r.data_recebimento, r.id;",
            (solicitacao_id,)
        )

        recebimentos = [
            _montar_recebimento(cursor, registro)
            for registro in cursor.fetchall()
        ]

        cursor.close()
        conexao.close()

        return recebimentos

    except psycopg2.Error as erro:
        conexao.close()

        logger.error(f"Erro ao listar recebimentos: {erro}")

        return None


def _validar(cursor, solicitacao_id: int, itens, data_recebimento):
    cursor.execute(
        """
        SELECT
            s.status,
            c.id,
            c.data_compra
        FROM solicitacoes_compra s
        LEFT JOIN compras c
            ON c.solicitacao_id = s.id
        WHERE s.id = %s
        FOR UPDATE OF s;
        """,
        (solicitacao_id,)
    )

    registro = cursor.fetchone()

    if registro is None:
        return None, None, "solicitacao_nao_encontrada"

    status, compra_id, data_compra = registro

    if status == "RECEBIDA":
        return None, None, "compra_ja_recebida"

    if status != "COMPRADA" or compra_id is None:
        return None, None, "status_nao_permite_recebimento"

    if data_recebimento < data_compra:
        return None, None, "data_anterior_a_compra"

    pendentes = _pendentes_por_produto(cursor, compra_id)

    if itens is None:
        itens = [
            {"produto_id": produto_id, "quantidade": quantidade}
            for produto_id, quantidade in pendentes.items()
            if quantidade > 0
        ]

    for item in itens:
        if item["produto_id"] not in pendentes:
            return None, None, "produto_fora_da_compra"

        if item["quantidade"] > pendentes[item["produto_id"]]:
            return None, None, "quantidade_maior_que_pendente"

    if not itens:
        return None, None, "compra_ja_recebida"

    return compra_id, itens, None


def registrar_recebimento(
    solicitacao_id: int,
    recebedor_id: int,
    data_recebimento: date | None,
    nota_fiscal: str | None,
    observacao: str | None,
    itens
):
    conexao = conectar()

    if conexao is None:
        return None, "erro_conexao"

    data_recebimento = data_recebimento or date.today()

    try:
        cursor = conexao.cursor()

        compra_id, itens, erro = _validar(
            cursor,
            solicitacao_id,
            itens,
            data_recebimento
        )

        if erro is not None:
            conexao.rollback()
            cursor.close()
            conexao.close()

            return None, erro

        cursor.execute(
            """
            INSERT INTO recebimentos (
                compra_id,
                recebedor_id,
                data_recebimento,
                nota_fiscal,
                observacao
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (
                compra_id,
                recebedor_id,
                data_recebimento,
                nota_fiscal,
                observacao
            )
        )

        recebimento_id = cursor.fetchone()[0]

        for item in itens:
            cursor.execute(
                """
                SELECT quantidade
                FROM produtos
                WHERE id = %s
                FOR UPDATE;
                """,
                (item["produto_id"],)
            )

            cursor.execute(
                """
                UPDATE produtos
                SET quantidade = quantidade + %s
                WHERE id = %s;
                """,
                (item["quantidade"], item["produto_id"])
            )

            cursor.execute(
                """
                INSERT INTO movimentacoes (
                    produto_id,
                    tipo,
                    quantidade,
                    recebimento_id,
                    usuario_id,
                    data_movimentacao
                )
                VALUES (
                    %s, 'ENTRADA', %s, %s, %s,
                    -- Recebimento lançado depois: a entrada fica na data em que chegou
                    CASE
                        WHEN %s::date >= CURRENT_DATE THEN CURRENT_TIMESTAMP
                        ELSE %s::date + LOCALTIME
                    END
                )
                RETURNING id;
                """,
                (
                    item["produto_id"],
                    item["quantidade"],
                    recebimento_id,
                    recebedor_id,
                    data_recebimento,
                    data_recebimento
                )
            )

            movimentacao_id = cursor.fetchone()[0]

            cursor.execute(
                """
                INSERT INTO itens_recebimento (
                    recebimento_id,
                    produto_id,
                    quantidade,
                    movimentacao_id
                )
                VALUES (%s, %s, %s, %s);
                """,
                (
                    recebimento_id,
                    item["produto_id"],
                    item["quantidade"],
                    movimentacao_id
                )
            )

        pendentes = _pendentes_por_produto(cursor, compra_id)

        if all(quantidade == 0 for quantidade in pendentes.values()):
            cursor.execute(
                """
                UPDATE solicitacoes_compra
                SET
                    status = 'RECEBIDA',
                    data_atualizacao = CURRENT_TIMESTAMP
                WHERE id = %s;
                """,
                (solicitacao_id,)
            )

        conexao.commit()

        cursor.close()
        conexao.close()

        return buscar_recebimento(recebimento_id), None

    except psycopg2.Error as erro:
        conexao.rollback()
        conexao.close()

        logger.error(f"Erro ao registrar recebimento: {erro}")

        return None, "erro_banco"
