import logging
from datetime import datetime, timedelta, timezone

import psycopg2

from backend.database import conectar


logger = logging.getLogger(__name__)

MARGEM_RENOVACAO = timedelta(minutes=5)


class ErroCredencial(Exception):
    pass


def salvar_credenciais(fonte: str, access_token: str, refresh_token: str | None, expira_em: datetime):
    conexao = conectar()

    if conexao is None:
        raise ErroCredencial("Sem conexão com o banco de dados.")

    try:
        cursor = conexao.cursor()
        cursor.execute(
            """
            INSERT INTO credenciais_externas (fonte, access_token, refresh_token, expira_em, atualizado_em)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (fonte) DO UPDATE SET
                access_token = EXCLUDED.access_token,
                refresh_token = EXCLUDED.refresh_token,
                expira_em = EXCLUDED.expira_em,
                atualizado_em = CURRENT_TIMESTAMP;
            """,
            (fonte, access_token, refresh_token, expira_em)
        )
        conexao.commit()
        cursor.close()
    finally:
        conexao.close()


def existem_credenciais(fonte: str) -> bool:
    conexao = conectar()

    if conexao is None:
        return False

    try:
        cursor = conexao.cursor()
        cursor.execute("SELECT 1 FROM credenciais_externas WHERE fonte = %s;", (fonte,))
        existe = cursor.fetchone() is not None
        cursor.close()
        return existe
    except psycopg2.Error:
        return False
    finally:
        conexao.close()


def obter_token_valido(fonte: str, renovar, forcar: bool = False) -> str:
    """Devolve um access token válido, renovando quando estiver perto de expirar.

    `renovar(refresh_token)` deve devolver (access_token, refresh_token, expira_em).
    A linha fica travada durante a renovação, porque o refresh token só pode
    ser usado uma vez: duas renovações ao mesmo tempo invalidariam a credencial.
    """
    conexao = conectar()

    if conexao is None:
        raise ErroCredencial("Sem conexão com o banco de dados.")

    try:
        cursor = conexao.cursor()
        cursor.execute(
            """
            SELECT access_token, refresh_token, expira_em
            FROM credenciais_externas
            WHERE fonte = %s
            FOR UPDATE;
            """,
            (fonte,)
        )

        registro = cursor.fetchone()

        if registro is None:
            conexao.rollback()
            raise ErroCredencial("nao_autorizada")

        access_token, refresh_token, expira_em = registro
        agora = datetime.now(timezone.utc)

        if not forcar and expira_em - MARGEM_RENOVACAO > agora:
            conexao.rollback()
            return access_token

        if not refresh_token:
            conexao.rollback()
            raise ErroCredencial("sem_refresh_token")

        novo_access, novo_refresh, nova_expiracao = renovar(refresh_token)

        cursor.execute(
            """
            UPDATE credenciais_externas
            SET access_token = %s,
                refresh_token = %s,
                expira_em = %s,
                atualizado_em = CURRENT_TIMESTAMP
            WHERE fonte = %s;
            """,
            (novo_access, novo_refresh or refresh_token, nova_expiracao, fonte)
        )
        conexao.commit()
        cursor.close()

        logger.info("Token de %s renovado; expira em %s.", fonte, nova_expiracao.isoformat())

        return novo_access

    except psycopg2.Error as erro:
        conexao.rollback()
        logger.error("Erro ao ler credenciais de %s: %s", fonte, erro)
        raise ErroCredencial("erro_banco") from erro

    finally:
        conexao.close()


def expiracao(segundos: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=int(segundos))
