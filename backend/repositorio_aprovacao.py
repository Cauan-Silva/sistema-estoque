import logging
import psycopg2

from backend.database import conectar
from backend.repositorio_cotacao import (
    buscar_cotacao,
    cotacao_completa,
    cotacao_vencida,
)
from backend.repositorio_solicitacao_compra import buscar_solicitacao

logger = logging.getLogger(__name__)


STATUS_PERMITEM_APROVACAO = ("EM_COTACAO",)
STATUS_PERMITEM_REPROVACAO = ("ABERTA", "EM_COTACAO")


def _travar_status(cursor, solicitacao_id: int, permitidos, usuario_id: int):
    cursor.execute(
        """
        SELECT status, solicitante_id
        FROM solicitacoes_compra
        WHERE id = %s
        FOR UPDATE;
        """,
        (solicitacao_id,)
    )

    registro = cursor.fetchone()

    if registro is None:
        return "solicitacao_nao_encontrada"

    if registro[1] == usuario_id:
        return "decisao_propria"

    if registro[0] not in permitidos:
        return "status_nao_permite_decisao"

    return None


def _registrar_decisao(
    solicitacao_id: int,
    usuario_id: int,
    novo_status: str,
    justificativa: str | None,
    permitidos,
    cotacao_id: int | None = None,
    validar=None
):
    conexao = conectar()

    if conexao is None:
        return None, "erro_conexao"

    try:
        cursor = conexao.cursor()

        erro = _travar_status(cursor, solicitacao_id, permitidos, usuario_id)

        if erro is None and validar is not None:
            erro = validar()

        if erro is not None:
            conexao.rollback()
            cursor.close()
            conexao.close()

            return None, erro

        cursor.execute(
            """
            UPDATE solicitacoes_compra
            SET
                status = %s,
                cotacao_aprovada_id = %s,
                decisao_por_id = %s,
                data_decisao = CURRENT_TIMESTAMP,
                justificativa_decisao = %s,
                data_atualizacao = CURRENT_TIMESTAMP
            WHERE id = %s;
            """,
            (
                novo_status,
                cotacao_id,
                usuario_id,
                justificativa,
                solicitacao_id
            )
        )

        conexao.commit()

        cursor.close()
        conexao.close()

        return buscar_solicitacao(solicitacao_id), None

    except psycopg2.Error as erro:
        conexao.rollback()
        conexao.close()

        logger.error(f"Erro ao registrar decisão da solicitação: {erro}")

        return None, "erro_banco"


def aprovar_solicitacao(
    solicitacao_id: int,
    cotacao_id: int,
    usuario_id: int,
    justificativa: str | None
):
    def validar():
        cotacao = buscar_cotacao(solicitacao_id, cotacao_id)

        if cotacao is None:
            return "cotacao_nao_encontrada"

        solicitacao = buscar_solicitacao(solicitacao_id)

        produtos_solicitados = [
            item["produto_id"] for item in solicitacao["itens"]
        ]

        if not cotacao_completa(cotacao, produtos_solicitados):
            return "cotacao_incompleta"

        if cotacao_vencida(cotacao):
            return "cotacao_vencida"

        return None

    return _registrar_decisao(
        solicitacao_id=solicitacao_id,
        usuario_id=usuario_id,
        novo_status="APROVADA",
        justificativa=justificativa,
        permitidos=STATUS_PERMITEM_APROVACAO,
        cotacao_id=cotacao_id,
        validar=validar
    )


def reprovar_solicitacao(
    solicitacao_id: int,
    usuario_id: int,
    justificativa: str
):
    return _registrar_decisao(
        solicitacao_id=solicitacao_id,
        usuario_id=usuario_id,
        novo_status="REPROVADA",
        justificativa=justificativa,
        permitidos=STATUS_PERMITEM_REPROVACAO
    )
