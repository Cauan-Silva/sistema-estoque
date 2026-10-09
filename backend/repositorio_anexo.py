import logging

import psycopg2

from backend.database import conectar

logger = logging.getLogger(__name__)

CAMPOS = """
    a.id, a.solicitacao_id, a.tipo, a.descricao, a.nome_arquivo, a.tipo_conteudo,
    a.tamanho, a.fornecedor_id, f.nome, a.usuario_id, u.nome, a.data_envio
"""

JUNCOES = """
    FROM anexos a
    LEFT JOIN fornecedores f ON f.id = a.fornecedor_id
    LEFT JOIN usuarios u ON u.id = a.usuario_id
"""


def _montar(r):
    return {
        "id": r[0],
        "solicitacao_id": r[1],
        "tipo": r[2],
        "descricao": r[3],
        "nome_arquivo": r[4],
        "tipo_conteudo": r[5],
        "tamanho": r[6],
        "fornecedor_id": r[7],
        "fornecedor": r[8],
        "usuario_id": r[9],
        "usuario": r[10],
        "data_envio": r[11],
    }


def listar_anexos(solicitacao_id: int):
    conexao = conectar()
    if conexao is None:
        return None
    try:
        cursor = conexao.cursor()
        cursor.execute("SELECT 1 FROM solicitacoes_compra WHERE id = %s;", (solicitacao_id,))
        if cursor.fetchone() is None:
            conexao.close()
            return None
        cursor.execute(
            f"SELECT {CAMPOS} {JUNCOES} WHERE a.solicitacao_id = %s ORDER BY a.data_envio DESC, a.id DESC;",
            (solicitacao_id,)
        )
        anexos = [_montar(r) for r in cursor.fetchall()]
        conexao.close()
        return anexos
    except psycopg2.Error as erro:
        conexao.close()
        logger.error(f"Erro ao listar anexos: {erro}")
        return None


def buscar_anexo(solicitacao_id: int, anexo_id: int, com_conteudo=False):
    conexao = conectar()
    if conexao is None:
        return None
    try:
        cursor = conexao.cursor()
        extra = ", a.conteudo" if com_conteudo else ""
        cursor.execute(
            f"SELECT {CAMPOS}{extra} {JUNCOES} WHERE a.solicitacao_id = %s AND a.id = %s;",
            (solicitacao_id, anexo_id)
        )
        registro = cursor.fetchone()
        conexao.close()
        if registro is None:
            return None
        anexo = _montar(registro)
        if com_conteudo:
            anexo["conteudo"] = bytes(registro[12])
        return anexo
    except psycopg2.Error as erro:
        conexao.close()
        logger.error(f"Erro ao buscar anexo: {erro}")
        return None


def salvar_anexo(solicitacao_id, tipo, descricao, nome_arquivo, tipo_conteudo, conteudo, fornecedor_id, usuario_id):
    conexao = conectar()
    if conexao is None:
        return None, "erro_conexao"
    try:
        cursor = conexao.cursor()
        cursor.execute("SELECT 1 FROM solicitacoes_compra WHERE id = %s;", (solicitacao_id,))
        if cursor.fetchone() is None:
            conexao.close()
            return None, "solicitacao_nao_encontrada"
        if fornecedor_id is not None:
            cursor.execute("SELECT 1 FROM fornecedores WHERE id = %s;", (fornecedor_id,))
            if cursor.fetchone() is None:
                conexao.close()
                return None, "fornecedor_nao_encontrado"
        cursor.execute(
            """
            INSERT INTO anexos (
                solicitacao_id, tipo, descricao, nome_arquivo, tipo_conteudo,
                tamanho, conteudo, fornecedor_id, usuario_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (
                solicitacao_id, tipo, descricao, nome_arquivo, tipo_conteudo,
                len(conteudo), psycopg2.Binary(conteudo), fornecedor_id, usuario_id,
            )
        )
        anexo_id = cursor.fetchone()[0]
        conexao.commit()
        conexao.close()
        return buscar_anexo(solicitacao_id, anexo_id), None
    except psycopg2.Error as erro:
        conexao.rollback()
        conexao.close()
        logger.error(f"Erro ao salvar anexo: {erro}")
        return None, "erro_banco"


def excluir_anexo(solicitacao_id: int, anexo_id: int) -> bool:
    conexao = conectar()
    if conexao is None:
        return False
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "DELETE FROM anexos WHERE solicitacao_id = %s AND id = %s;",
            (solicitacao_id, anexo_id)
        )
        excluido = cursor.rowcount > 0
        conexao.commit()
        conexao.close()
        return excluido
    except psycopg2.Error as erro:
        conexao.rollback()
        conexao.close()
        logger.error(f"Erro ao excluir anexo: {erro}")
        return False
