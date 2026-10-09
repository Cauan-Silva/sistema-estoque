import logging
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


load_dotenv()


def conectar():
    try:
        conexao = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )

        return conexao

    except psycopg2.Error as erro:
        logger.error(f"Erro ao conectar ao banco de dados: {erro}")
        return None


RAIZ_PROJETO = Path(__file__).resolve().parent.parent


def aplicar_migracoes():
    """Leva o banco para a versão mais recente das migrations (alembic upgrade head)."""
    from alembic import command
    from alembic.config import Config

    configuracao = Config(str(RAIZ_PROJETO / "alembic.ini"))
    configuracao.set_main_option(
        "script_location",
        str(RAIZ_PROJETO / "migrations")
    )

    command.upgrade(configuracao, "head")

    logger.info("Banco de dados na versão mais recente das migrations.")
