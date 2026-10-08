from datetime import date, timedelta
from decimal import Decimal

import psycopg2

from backend.database import conectar
from backend.repositorio_cotacao import buscar_cotacao


SITUACAO_RECEBIMENTO = """
    CASE
        WHEN tr.recebido = 0 THEN 'PENDENTE'
        WHEN tr.recebido < tc.comprado THEN 'PARCIAL'
        ELSE 'COMPLETO'
    END
"""

CONSULTA_COMPRA = f"""
    SELECT
        c.id,
        c.solicitacao_id,
        c.cotacao_id,
        c.fornecedor_id,
        f.nome,
        c.comprador_id,
        u.nome,
        c.numero_pedido,
        c.data_compra,
        c.previsao_entrega,
        c.valor_itens,
        c.frete,
        c.valor_total,
        c.observacao,
        c.data_criacao,
        {SITUACAO_RECEBIMENTO} AS situacao_recebimento,
        tr.ultimo_recebimento,
        c.forma_pagamento_id,
        c.forma_pagamento
    FROM compras c
    JOIN fornecedores f
        ON f.id = c.fornecedor_id
    JOIN usuarios u
        ON u.id = c.comprador_id
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
"""


def _buscar_itens(cursor, compra_id: int):
    cursor.execute(
        """
        SELECT
            i.produto_id,
            p.nome,
            i.quantidade,
            i.preco_unitario,
            i.subtotal,
            COALESCE((
                SELECT SUM(ir.quantidade)
                FROM itens_recebimento ir
                JOIN recebimentos r
                    ON r.id = ir.recebimento_id
                WHERE r.compra_id = i.compra_id
                  AND ir.produto_id = i.produto_id
            ), 0)
        FROM itens_compra i
        JOIN produtos p
            ON p.id = i.produto_id
        WHERE i.compra_id = %s
        ORDER BY i.id;
        """,
        (compra_id,)
    )

    return [
        {
            "produto_id": registro[0],
            "produto": registro[1],
            "quantidade": registro[2],
            "preco_unitario": float(registro[3]),
            "subtotal": float(registro[4]),
            "quantidade_recebida": int(registro[5]),
            "quantidade_pendente": registro[2] - int(registro[5])
        }
        for registro in cursor.fetchall()
    ]


def _montar_compra(cursor, registro):
    situacao = registro[15]
    ultimo_recebimento = registro[16]

    entregue_no_prazo = None

    if situacao == "COMPLETO" and ultimo_recebimento is not None:
        entregue_no_prazo = ultimo_recebimento <= registro[9]

    return {
        "id": registro[0],
        "solicitacao_id": registro[1],
        "cotacao_id": registro[2],
        "fornecedor_id": registro[3],
        "fornecedor": registro[4],
        "comprador_id": registro[5],
        "comprador": registro[6],
        "numero_pedido": registro[7],
        "data_compra": registro[8],
        "previsao_entrega": registro[9],
        "valor_itens": float(registro[10]),
        "frete": float(registro[11]),
        "valor_total": float(registro[12]),
        "observacao": registro[13],
        "data_criacao": registro[14],
        "situacao_recebimento": situacao,
        "ultimo_recebimento": ultimo_recebimento,
        "entregue_no_prazo": entregue_no_prazo,
        "forma_pagamento_id": registro[17],
        "forma_pagamento": registro[18],
        "itens": _buscar_itens(cursor, registro[0])
    }


def _buscar_uma(condicao: str, parametro):
    conexao = conectar()

    if conexao is None:
        return None

    try:
        cursor = conexao.cursor()

        cursor.execute(
            CONSULTA_COMPRA + f" WHERE {condicao} = %s;",
            (parametro,)
        )

        registro = cursor.fetchone()

        compra = (
            _montar_compra(cursor, registro)
            if registro is not None
            else None
        )

        cursor.close()
        conexao.close()

        return compra

    except psycopg2.Error as erro:
        conexao.close()

        print(f"Erro ao buscar compra: {erro}")

        return None


def buscar_compra(compra_id: int):
    return _buscar_uma("c.id", compra_id)


def buscar_compra_por_solicitacao(solicitacao_id: int):
    return _buscar_uma("c.solicitacao_id", solicitacao_id)


def listar_compras(
    fornecedor_id: int | None = None,
    situacao_recebimento: str | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    pagina: int = 1,
    tamanho: int = 10
):
    conexao = conectar()

    if conexao is None:
        return []

    try:
        cursor = conexao.cursor()

        condicoes = []
        parametros = []

        if fornecedor_id is not None:
            condicoes.append("c.fornecedor_id = %s")
            parametros.append(fornecedor_id)

        if situacao_recebimento is not None:
            condicoes.append(f"({SITUACAO_RECEBIMENTO}) = %s")
            parametros.append(situacao_recebimento)

        if data_inicio is not None:
            condicoes.append("c.data_compra >= %s")
            parametros.append(data_inicio)

        if data_fim is not None:
            condicoes.append("c.data_compra <= %s")
            parametros.append(data_fim)

        consulta = CONSULTA_COMPRA

        if condicoes:
            consulta += " WHERE " + " AND ".join(condicoes)

        consulta += """
            ORDER BY c.data_compra DESC, c.id DESC
            LIMIT %s
            OFFSET %s;
        """

        parametros.append(tamanho)
        parametros.append((pagina - 1) * tamanho)

        cursor.execute(consulta, tuple(parametros))

        compras = [
            _montar_compra(cursor, registro)
            for registro in cursor.fetchall()
        ]

        cursor.close()
        conexao.close()

        return compras

    except psycopg2.Error as erro:
        conexao.close()

        print(f"Erro ao listar compras: {erro}")

        return []


def registrar_compra(
    solicitacao_id: int,
    comprador_id: int,
    numero_pedido: str | None,
    data_compra: date | None,
    previsao_entrega: date | None,
    observacao: str | None
):
    conexao = conectar()

    if conexao is None:
        return None, "erro_conexao"

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            SELECT
                status,
                cotacao_aprovada_id
            FROM solicitacoes_compra
            WHERE id = %s
            FOR UPDATE;
            """,
            (solicitacao_id,)
        )

        registro = cursor.fetchone()

        erro = None

        if registro is None:
            erro = "solicitacao_nao_encontrada"

        elif registro[0] != "APROVADA" or registro[1] is None:
            erro = "status_nao_permite_compra"

        cotacao = None

        if erro is None:
            cotacao = buscar_cotacao(solicitacao_id, registro[1])

            if cotacao is None:
                erro = "erro_banco"

        if erro is None:
            data_compra = data_compra or date.today()

            previsao_entrega = previsao_entrega or (
                data_compra
                + timedelta(days=cotacao["prazo_entrega_dias"])
            )

            if previsao_entrega < data_compra:
                erro = "previsao_invalida"

        if erro is not None:
            conexao.rollback()
            cursor.close()
            conexao.close()

            return None, erro

        cursor.execute(
            """
            INSERT INTO compras (
                solicitacao_id,
                cotacao_id,
                fornecedor_id,
                comprador_id,
                numero_pedido,
                data_compra,
                previsao_entrega,
                valor_itens,
                frete,
                valor_total,
                observacao,
                forma_pagamento_id,
                forma_pagamento
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (
                solicitacao_id,
                cotacao["id"],
                cotacao["fornecedor_id"],
                comprador_id,
                numero_pedido,
                data_compra,
                previsao_entrega,
                Decimal(str(cotacao["valor_itens"])),
                Decimal(str(cotacao["frete"])),
                Decimal(str(cotacao["valor_total"])),
                observacao,
                cotacao["forma_pagamento_id"],
                cotacao["forma_pagamento"]
            )
        )

        compra_id = cursor.fetchone()[0]

        for item in cotacao["itens"]:
            cursor.execute(
                """
                INSERT INTO itens_compra (
                    compra_id,
                    produto_id,
                    quantidade,
                    preco_unitario,
                    subtotal
                )
                VALUES (%s, %s, %s, %s, %s);
                """,
                (
                    compra_id,
                    item["produto_id"],
                    item["quantidade"],
                    Decimal(str(item["preco_unitario"])),
                    Decimal(str(item["subtotal"]))
                )
            )

        cursor.execute(
            """
            UPDATE solicitacoes_compra
            SET
                status = 'COMPRADA',
                data_atualizacao = CURRENT_TIMESTAMP
            WHERE id = %s;
            """,
            (solicitacao_id,)
        )

        conexao.commit()

        cursor.close()
        conexao.close()

        return buscar_compra(compra_id), None

    except psycopg2.Error as erro:
        conexao.rollback()
        conexao.close()

        print(f"Erro ao registrar compra: {erro}")

        return None, "erro_banco"
