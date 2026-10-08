import logging
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

import psycopg2

from backend.database import conectar
from backend.repositorio_solicitacao_compra import buscar_solicitacao

logger = logging.getLogger(__name__)


STATUS_PERMITEM_COTACAO = ("ABERTA", "EM_COTACAO")

CENTAVOS = Decimal("0.01")


def _dinheiro(valor) -> float:
    return float(
        Decimal(valor).quantize(CENTAVOS, rounding=ROUND_HALF_UP)
    )


CONSULTA_COTACAO = """
    SELECT
        c.id,
        c.solicitacao_id,
        c.fornecedor_id,
        f.nome,
        c.frete,
        c.prazo_entrega_dias,
        c.validade,
        c.observacao,
        c.data_criacao,
        c.data_atualizacao,
        c.forma_pagamento_id,
        fp.codigo || ' - ' || fp.titulo
    FROM cotacoes c
    JOIN fornecedores f
        ON f.id = c.fornecedor_id
    LEFT JOIN formas_pagamento fp
        ON fp.id = c.forma_pagamento_id
"""


def _buscar_itens(cursor, cotacao_id: int, solicitacao_id: int):
    cursor.execute(
        """
        SELECT
            ic.produto_id,
            p.nome,
            isc.quantidade,
            ic.preco_unitario
        FROM itens_cotacao ic
        JOIN produtos p
            ON p.id = ic.produto_id
        JOIN itens_solicitacao_compra isc
            ON isc.produto_id = ic.produto_id
           AND isc.solicitacao_id = %s
        WHERE ic.cotacao_id = %s
        ORDER BY isc.id;
        """,
        (solicitacao_id, cotacao_id)
    )

    return [
        {
            "produto_id": registro[0],
            "produto": registro[1],
            "quantidade": registro[2],
            "preco_unitario": _dinheiro(registro[3]),
            "subtotal": _dinheiro(registro[2] * registro[3])
        }
        for registro in cursor.fetchall()
    ]


def _montar_cotacao(cursor, registro):
    itens = _buscar_itens(cursor, registro[0], registro[1])

    valor_itens = sum(
        (Decimal(str(item["subtotal"])) for item in itens),
        Decimal("0")
    )
    frete = Decimal(registro[4])

    return {
        "id": registro[0],
        "solicitacao_id": registro[1],
        "fornecedor_id": registro[2],
        "fornecedor": registro[3],
        "frete": _dinheiro(frete),
        "prazo_entrega_dias": registro[5],
        "validade": registro[6],
        "observacao": registro[7],
        "data_criacao": registro[8],
        "data_atualizacao": registro[9],
        "forma_pagamento_id": registro[10],
        "forma_pagamento": registro[11],
        "itens": itens,
        "valor_itens": _dinheiro(valor_itens),
        "valor_total": _dinheiro(valor_itens + frete)
    }


def _travar_solicitacao(cursor, solicitacao_id: int):
    cursor.execute(
        """
        SELECT status
        FROM solicitacoes_compra
        WHERE id = %s
        FOR UPDATE;
        """,
        (solicitacao_id,)
    )

    registro = cursor.fetchone()

    if registro is None:
        return "solicitacao_nao_encontrada"

    if registro[0] not in STATUS_PERMITEM_COTACAO:
        return "solicitacao_nao_permite_cotacao"

    return None


def _validar_itens(cursor, solicitacao_id: int, itens):
    cursor.execute(
        """
        SELECT produto_id
        FROM itens_solicitacao_compra
        WHERE solicitacao_id = %s;
        """,
        (solicitacao_id,)
    )

    produtos_solicitados = {
        registro[0] for registro in cursor.fetchall()
    }

    for item in itens:
        if item["produto_id"] not in produtos_solicitados:
            return "produto_fora_da_solicitacao"

    return None


def _validar_fornecedor(cursor, fornecedor_id: int):
    cursor.execute(
        """
        SELECT ativo
        FROM fornecedores
        WHERE id = %s;
        """,
        (fornecedor_id,)
    )

    registro = cursor.fetchone()

    if registro is None:
        return "fornecedor_nao_encontrado"

    if not registro[0]:
        return "fornecedor_inativo"

    return None


def _validar_forma_pagamento(cursor, forma_pagamento_id: int | None):
    if forma_pagamento_id is None:
        return None

    cursor.execute(
        """
        SELECT ativo
        FROM formas_pagamento
        WHERE id = %s;
        """,
        (forma_pagamento_id,)
    )

    registro = cursor.fetchone()

    if registro is None:
        return "forma_pagamento_nao_encontrada"

    if not registro[0]:
        return "forma_pagamento_inativa"

    return None


def _inserir_itens(cursor, cotacao_id: int, itens):
    for item in itens:
        cursor.execute(
            """
            INSERT INTO itens_cotacao (
                cotacao_id,
                produto_id,
                preco_unitario
            )
            VALUES (%s, %s, %s);
            """,
            (
                cotacao_id,
                item["produto_id"],
                item["preco_unitario"]
            )
        )


def _finalizar_com_erro(conexao, cursor, erro):
    conexao.rollback()
    cursor.close()
    conexao.close()

    return None, erro


def criar_cotacao(
    solicitacao_id: int,
    fornecedor_id: int,
    frete: float,
    prazo_entrega_dias: int,
    validade,
    observacao: str | None,
    itens,
    forma_pagamento_id: int | None = None
):
    conexao = conectar()

    if conexao is None:
        return None, "erro_conexao"

    try:
        cursor = conexao.cursor()

        erro = (
            _travar_solicitacao(cursor, solicitacao_id)
            or _validar_fornecedor(cursor, fornecedor_id)
            or _validar_itens(cursor, solicitacao_id, itens)
            or _validar_forma_pagamento(cursor, forma_pagamento_id)
        )

        if erro is not None:
            return _finalizar_com_erro(conexao, cursor, erro)

        cursor.execute(
            """
            SELECT 1
            FROM cotacoes
            WHERE solicitacao_id = %s
              AND fornecedor_id = %s;
            """,
            (solicitacao_id, fornecedor_id)
        )

        if cursor.fetchone() is not None:
            return _finalizar_com_erro(
                conexao,
                cursor,
                "cotacao_duplicada"
            )

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
                fornecedor_id,
                frete,
                prazo_entrega_dias,
                validade,
                observacao,
                forma_pagamento_id
            )
        )

        cotacao_id = cursor.fetchone()[0]

        _inserir_itens(cursor, cotacao_id, itens)

        cursor.execute(
            """
            UPDATE solicitacoes_compra
            SET
                status = 'EM_COTACAO',
                data_atualizacao = CURRENT_TIMESTAMP
            WHERE id = %s
              AND status = 'ABERTA';
            """,
            (solicitacao_id,)
        )

        conexao.commit()

        cursor.close()
        conexao.close()

        return buscar_cotacao(solicitacao_id, cotacao_id), None

    except psycopg2.Error as erro:
        conexao.rollback()
        conexao.close()

        logger.error(f"Erro ao criar cotação: {erro}")

        return None, "erro_banco"


def buscar_cotacao(solicitacao_id: int, cotacao_id: int):
    conexao = conectar()

    if conexao is None:
        return None

    try:
        cursor = conexao.cursor()

        cursor.execute(
            CONSULTA_COTACAO
            + " WHERE c.id = %s AND c.solicitacao_id = %s;",
            (cotacao_id, solicitacao_id)
        )

        registro = cursor.fetchone()

        cotacao = (
            _montar_cotacao(cursor, registro)
            if registro is not None
            else None
        )

        cursor.close()
        conexao.close()

        return cotacao

    except psycopg2.Error as erro:
        conexao.close()

        logger.error(f"Erro ao buscar cotação: {erro}")

        return None


def listar_cotacoes(solicitacao_id: int):
    conexao = conectar()

    if conexao is None:
        return None

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            SELECT 1
            FROM solicitacoes_compra
            WHERE id = %s;
            """,
            (solicitacao_id,)
        )

        if cursor.fetchone() is None:
            cursor.close()
            conexao.close()

            return None

        cursor.execute(
            CONSULTA_COTACAO
            + " WHERE c.solicitacao_id = %s ORDER BY c.id;",
            (solicitacao_id,)
        )

        cotacoes = [
            _montar_cotacao(cursor, registro)
            for registro in cursor.fetchall()
        ]

        cursor.close()
        conexao.close()

        return cotacoes

    except psycopg2.Error as erro:
        conexao.close()

        logger.error(f"Erro ao listar cotações: {erro}")

        return None


def _cotacao_existe(cursor, solicitacao_id: int, cotacao_id: int):
    cursor.execute(
        """
        SELECT 1
        FROM cotacoes
        WHERE id = %s
          AND solicitacao_id = %s;
        """,
        (cotacao_id, solicitacao_id)
    )

    return cursor.fetchone() is not None


def atualizar_cotacao(
    solicitacao_id: int,
    cotacao_id: int,
    frete: float,
    prazo_entrega_dias: int,
    validade,
    observacao: str | None,
    itens,
    forma_pagamento_id: int | None = None
):
    conexao = conectar()

    if conexao is None:
        return None, "erro_conexao"

    try:
        cursor = conexao.cursor()

        erro = _travar_solicitacao(cursor, solicitacao_id)

        if erro is None and not _cotacao_existe(
            cursor,
            solicitacao_id,
            cotacao_id
        ):
            erro = "cotacao_nao_encontrada"

        if erro is None:
            erro = _validar_itens(cursor, solicitacao_id, itens)

        if erro is None:
            cursor.execute(
                "SELECT forma_pagamento_id FROM cotacoes WHERE id = %s;",
                (cotacao_id,)
            )

            forma_atual = cursor.fetchone()[0]

            if forma_pagamento_id != forma_atual:
                erro = _validar_forma_pagamento(cursor, forma_pagamento_id)

        if erro is not None:
            return _finalizar_com_erro(conexao, cursor, erro)

        cursor.execute(
            """
            UPDATE cotacoes
            SET
                frete = %s,
                prazo_entrega_dias = %s,
                validade = %s,
                observacao = %s,
                forma_pagamento_id = %s,
                data_atualizacao = CURRENT_TIMESTAMP
            WHERE id = %s;
            """,
            (
                frete,
                prazo_entrega_dias,
                validade,
                observacao,
                forma_pagamento_id,
                cotacao_id
            )
        )

        cursor.execute(
            """
            DELETE FROM itens_cotacao
            WHERE cotacao_id = %s;
            """,
            (cotacao_id,)
        )

        _inserir_itens(cursor, cotacao_id, itens)

        conexao.commit()

        cursor.close()
        conexao.close()

        return buscar_cotacao(solicitacao_id, cotacao_id), None

    except psycopg2.Error as erro:
        conexao.rollback()
        conexao.close()

        logger.error(f"Erro ao atualizar cotação: {erro}")

        return None, "erro_banco"


def excluir_cotacao(solicitacao_id: int, cotacao_id: int):
    conexao = conectar()

    if conexao is None:
        return "erro_conexao"

    try:
        cursor = conexao.cursor()

        erro = _travar_solicitacao(cursor, solicitacao_id)

        if erro is None and not _cotacao_existe(
            cursor,
            solicitacao_id,
            cotacao_id
        ):
            erro = "cotacao_nao_encontrada"

        if erro is not None:
            _finalizar_com_erro(conexao, cursor, erro)
            return erro

        cursor.execute(
            """
            DELETE FROM cotacoes
            WHERE id = %s;
            """,
            (cotacao_id,)
        )

        cursor.execute(
            """
            UPDATE solicitacoes_compra
            SET
                status = 'ABERTA',
                data_atualizacao = CURRENT_TIMESTAMP
            WHERE id = %s
              AND status = 'EM_COTACAO'
              AND NOT EXISTS (
                  SELECT 1
                  FROM cotacoes
                  WHERE solicitacao_id = %s
              );
            """,
            (solicitacao_id, solicitacao_id)
        )

        conexao.commit()

        cursor.close()
        conexao.close()

        return None

    except psycopg2.Error as erro:
        conexao.rollback()
        conexao.close()

        logger.error(f"Erro ao excluir cotação: {erro}")

        return "erro_banco"


def cotacao_vencida(cotacao, hoje=None) -> bool:
    hoje = hoje or date.today()

    return (
        cotacao["validade"] is not None
        and cotacao["validade"] < hoje
    )


def cotacao_completa(cotacao, produtos_solicitados) -> bool:
    produtos_cotados = {
        item["produto_id"] for item in cotacao["itens"]
    }

    return produtos_cotados == set(produtos_solicitados)


def _resumo(cotacao):
    return {
        "cotacao_id": cotacao["id"],
        "fornecedor_id": cotacao["fornecedor_id"],
        "fornecedor": cotacao["fornecedor"],
        "valor_total": cotacao["valor_total"],
        "frete": cotacao["frete"],
        "prazo_entrega_dias": cotacao["prazo_entrega_dias"],
        "validade": cotacao["validade"],
        "forma_pagamento": cotacao["forma_pagamento"],
    }


def comparar_cotacoes(solicitacao_id: int):
    solicitacao = buscar_solicitacao(solicitacao_id)

    if solicitacao is None:
        return None

    cotacoes = listar_cotacoes(solicitacao_id) or []

    produtos_solicitados = [
        item["produto_id"] for item in solicitacao["itens"]
    ]

    ranking = []

    for cotacao in cotacoes:
        completa = cotacao_completa(cotacao, produtos_solicitados)
        vencida = cotacao_vencida(cotacao)

        ranking.append({
            **_resumo(cotacao),
            "valor_itens": cotacao["valor_itens"],
            "itens_cotados": len(cotacao["itens"]),
            "cobre_todos_itens": completa,
            "vencida": vencida,
            "elegivel": completa and not vencida,
        })

    ranking.sort(
        key=lambda c: (
            not c["elegivel"],
            c["valor_total"],
            c["prazo_entrega_dias"],
        )
    )

    elegiveis = [c for c in ranking if c["elegivel"]]

    def destaque(chave):
        if not elegiveis:
            return None

        melhor = min(
            elegiveis,
            key=lambda c: (c[chave], c["valor_total"])
        )

        return {
            campo: melhor[campo]
            for campo in (
                "cotacao_id",
                "fornecedor_id",
                "fornecedor",
                "valor_total",
                "frete",
                "prazo_entrega_dias",
                "validade",
                "forma_pagamento",
            )
        }

    por_produto = []

    for item in solicitacao["itens"]:
        ofertas = [
            (cotacao, item_cotado)
            for cotacao in cotacoes
            if not cotacao_vencida(cotacao)
            for item_cotado in cotacao["itens"]
            if item_cotado["produto_id"] == item["produto_id"]
        ]

        melhor = (
            min(
                ofertas,
                key=lambda oferta: (
                    oferta[1]["preco_unitario"],
                    oferta[0]["prazo_entrega_dias"],
                )
            )
            if ofertas
            else None
        )

        por_produto.append({
            "produto_id": item["produto_id"],
            "produto": item["produto"],
            "quantidade": item["quantidade"],
            "quantidade_ofertas": len(ofertas),
            "melhor_preco_unitario": (
                melhor[1]["preco_unitario"] if melhor else None
            ),
            "cotacao_id": melhor[0]["id"] if melhor else None,
            "fornecedor_id": (
                melhor[0]["fornecedor_id"] if melhor else None
            ),
            "fornecedor": melhor[0]["fornecedor"] if melhor else None,
        })

    return {
        "solicitacao_id": solicitacao_id,
        "status_solicitacao": solicitacao["status"],
        "total_cotacoes": len(cotacoes),
        "cotacoes_elegiveis": len(elegiveis),
        "menor_valor_total": destaque("valor_total"),
        "menor_prazo": destaque("prazo_entrega_dias"),
        "menor_frete": destaque("frete"),
        "cotacoes": ranking,
        "por_produto": por_produto,
    }
