"""Preços de referência anotados à mão (ex.: o que foi visto no Mercado Livre)."""

import logging
from decimal import ROUND_HALF_UP, Decimal

import psycopg2

from backend.database import conectar

logger = logging.getLogger(__name__)

CONSULTA = """
    SELECT r.id, r.produto_id, r.valor, r.fonte, r.link, r.observacao, u.nome, r.data_registro
    FROM precos_referencia r
    LEFT JOIN usuarios u ON u.id = r.usuario_id
"""


def _montar(registro):
    return {
        "id": registro[0],
        "produto_id": registro[1],
        "valor": float(Decimal(registro[2]).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)),
        "fonte": registro[3],
        "link": registro[4],
        "observacao": registro[5],
        "usuario": registro[6],
        "data_registro": registro[7],
    }


def listar_referencias(produto_id: int, limite: int = 10):
    conexao = conectar()
    if conexao is None:
        return []
    try:
        cursor = conexao.cursor()
        cursor.execute(
            CONSULTA + " WHERE r.produto_id = %s ORDER BY r.data_registro DESC, r.id DESC LIMIT %s;",
            (produto_id, limite),
        )
        referencias = [_montar(r) for r in cursor.fetchall()]
        cursor.close()
        conexao.close()
        return referencias
    except psycopg2.Error as erro:
        conexao.close()
        logger.error(f"Erro ao listar preços de referência: {erro}")
        return []


def registrar_referencia(produto_id, valor, fonte, link, observacao, usuario_id):
    conexao = conectar()
    if conexao is None:
        return None, "erro_conexao"
    try:
        cursor = conexao.cursor()
        cursor.execute("SELECT 1 FROM produtos WHERE id = %s;", (produto_id,))
        if cursor.fetchone() is None:
            conexao.close()
            return None, "produto_nao_encontrado"

        cursor.execute(
            """
            INSERT INTO precos_referencia (produto_id, valor, fonte, link, observacao, usuario_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (produto_id, valor, fonte, link, observacao, usuario_id),
        )
        referencia_id = cursor.fetchone()[0]
        conexao.commit()
        cursor.execute(CONSULTA + " WHERE r.id = %s;", (referencia_id,))
        referencia = _montar(cursor.fetchone())
        cursor.close()
        conexao.close()
        return referencia, None
    except psycopg2.Error as erro:
        conexao.rollback()
        conexao.close()
        logger.error(f"Erro ao registrar preço de referência: {erro}")
        return None, "erro_banco"


def excluir_referencia(referencia_id: int) -> bool:
    conexao = conectar()
    if conexao is None:
        return False
    try:
        cursor = conexao.cursor()
        cursor.execute("DELETE FROM precos_referencia WHERE id = %s;", (referencia_id,))
        excluida = cursor.rowcount > 0
        conexao.commit()
        cursor.close()
        conexao.close()
        return excluida
    except psycopg2.Error as erro:
        conexao.rollback()
        conexao.close()
        logger.error(f"Erro ao excluir preço de referência: {erro}")
        return False
