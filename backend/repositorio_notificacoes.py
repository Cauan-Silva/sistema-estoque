"""Pendências de cada usuário, calculadas a partir da situação atual.

Não há fila de mensagens: uma notificação existe enquanto a ação estiver
pendente e some sozinha quando alguém agir (cotar, aprovar, comprar, receber).
"""

import logging
from datetime import date

import psycopg2

from backend.database import conectar
from backend.permissoes import permissoes_do_perfil

logger = logging.getLogger(__name__)

LIMITE_POR_TIPO = 15


def _data(valor) -> str:
    return valor.strftime("%d/%m/%Y") if valor else ""


def _para_cotar(cursor):
    cursor.execute(
        """
        SELECT s.id, s.data_criacao, u.nome, COUNT(i.id)
        FROM solicitacoes_compra s
        JOIN usuarios u ON u.id = s.solicitante_id
        LEFT JOIN itens_solicitacao_compra i ON i.solicitacao_id = s.id
        WHERE s.status = 'ABERTA'
        GROUP BY s.id, s.data_criacao, u.nome
        ORDER BY s.data_criacao
        LIMIT %s;
        """,
        (LIMITE_POR_TIPO,)
    )
    return [
        {
            "tipo": "cotar",
            "titulo": f"Solicitação Nº {r[0]} aguardando cotação",
            "descricao": f"{r[3]} item(ns), pedida por {r[2]} em {_data(r[1])}.",
            "link": f"#/solicitacoes/{r[0]}",
            "urgente": False,
            "data": r[1],
        }
        for r in cursor.fetchall()
    ]


def _para_aprovar(cursor, usuario_id: int, administrador: bool):
    cursor.execute(
        """
        SELECT s.id, s.data_atualizacao, COUNT(c.id), MIN(c.valor_total_calculado)
        FROM solicitacoes_compra s
        JOIN (
            SELECT c.id, c.solicitacao_id,
                   c.frete + COALESCE(SUM(ic.preco_unitario * isc.quantidade), 0) AS valor_total_calculado
            FROM cotacoes c
            LEFT JOIN itens_cotacao ic ON ic.cotacao_id = c.id
            LEFT JOIN itens_solicitacao_compra isc
                ON isc.solicitacao_id = c.solicitacao_id AND isc.produto_id = ic.produto_id
            GROUP BY c.id, c.solicitacao_id, c.frete
        ) c ON c.solicitacao_id = s.id
        WHERE s.status = 'EM_COTACAO'
          AND (%s OR s.solicitante_id <> %s)
        GROUP BY s.id, s.data_atualizacao
        ORDER BY s.data_atualizacao
        LIMIT %s;
        """,
        (administrador, usuario_id, LIMITE_POR_TIPO)
    )
    itens = []
    for r in cursor.fetchall():
        menor = f", menor total R$ {float(r[3]):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if r[3] is not None else ""
        itens.append({
            "tipo": "aprovar",
            "titulo": f"Solicitação Nº {r[0]} aguardando aprovação",
            "descricao": f"{r[2]} cotação(ões) para comparar{menor}.",
            "link": f"#/solicitacoes/{r[0]}",
            "urgente": False,
            "data": r[1],
        })
    return itens


def _para_comprar(cursor):
    cursor.execute(
        """
        SELECT s.id, s.data_decisao, f.nome
        FROM solicitacoes_compra s
        LEFT JOIN cotacoes c ON c.id = s.cotacao_aprovada_id
        LEFT JOIN fornecedores f ON f.id = c.fornecedor_id
        WHERE s.status = 'APROVADA'
        ORDER BY s.data_decisao NULLS LAST
        LIMIT %s;
        """,
        (LIMITE_POR_TIPO,)
    )
    return [
        {
            "tipo": "comprar",
            "titulo": f"Solicitação Nº {r[0]} aprovada: registrar a compra",
            "descricao": f"Fornecedor escolhido: {r[2]}." if r[2] else "Cotação aprovada.",
            "link": f"#/solicitacoes/{r[0]}",
            "urgente": False,
            "data": r[1],
        }
        for r in cursor.fetchall()
    ]


def _para_receber(cursor, hoje: date):
    cursor.execute(
        """
        SELECT s.id, c.previsao_entrega, f.nome
        FROM solicitacoes_compra s
        JOIN compras c ON c.solicitacao_id = s.id
        JOIN fornecedores f ON f.id = c.fornecedor_id
        WHERE s.status = 'COMPRADA'
        ORDER BY c.previsao_entrega
        LIMIT %s;
        """,
        (LIMITE_POR_TIPO,)
    )
    itens = []
    for r in cursor.fetchall():
        atrasada = r[1] is not None and r[1] < hoje
        itens.append({
            "tipo": "receber",
            "titulo": f"Solicitação Nº {r[0]}: {'entrega atrasada' if atrasada else 'aguardando entrega'}",
            "descricao": f"{r[2]}, previsão {_data(r[1])}. Registre o recebimento quando chegar.",
            "link": f"#/solicitacoes/{r[0]}",
            "urgente": atrasada,
            "data": r[1],
        })
    return itens


def _estoque_baixo(cursor):
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM produtos p
        WHERE p.quantidade <= p.estoque_minimo
          AND NOT EXISTS (
              SELECT 1
              FROM itens_solicitacao_compra i
              JOIN solicitacoes_compra s ON s.id = i.solicitacao_id
              WHERE i.produto_id = p.id
                AND s.status IN ('ABERTA', 'EM_COTACAO', 'APROVADA', 'COMPRADA')
          );
        """
    )
    quantidade = cursor.fetchone()[0]
    if not quantidade:
        return []
    return [{
        "tipo": "repor",
        "titulo": f"{quantidade} produto(s) no estoque mínimo sem pedido aberto",
        "descricao": "Veja a sugestão de compra e crie a solicitação.",
        "link": "#/sugestoes-compra",
        "urgente": True,
        "data": None,
    }]


def notificacoes_do_usuario(usuario, hoje: date | None = None):
    usuario_id, perfil = usuario[0], usuario[6]
    permissoes = set(permissoes_do_perfil(perfil))
    hoje = hoje or date.today()

    conexao = conectar()
    if conexao is None:
        return None

    try:
        cursor = conexao.cursor()
        itens = []

        if "solicitacoes.editar" in permissoes:
            itens += _estoque_baixo(cursor)
        if "recebimentos.registrar" in permissoes:
            itens += _para_receber(cursor, hoje)
        if "compras.aprovar" in permissoes:
            itens += _para_aprovar(cursor, usuario_id, perfil == "ADMINISTRADOR")
        if "compras.registrar" in permissoes:
            itens += _para_comprar(cursor)
        if "cotacoes.editar" in permissoes:
            itens += _para_cotar(cursor)

        cursor.close()
        conexao.close()

        itens.sort(key=lambda item: not item["urgente"])
        for item in itens:
            item.pop("data", None)

        return {"total": len(itens), "itens": itens}

    except psycopg2.Error as erro:
        conexao.close()
        logger.error(f"Erro ao calcular notificações: {erro}")
        return None
