import os
from urllib.parse import quote_plus

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool


load_dotenv()


def url_do_banco() -> str:
    usuario = quote_plus(os.getenv("DB_USER", "postgres"))
    senha = quote_plus(os.getenv("DB_PASSWORD", ""))
    host = os.getenv("DB_HOST", "localhost")
    porta = os.getenv("DB_PORT", "5432")
    banco = os.getenv("DB_NAME", "sistema_estoque")

    return f"postgresql+psycopg2://{usuario}:{senha}@{host}:{porta}/{banco}"


def executar_offline():
    """Gera o SQL das migrations sem conectar ao banco (alembic upgrade --sql)."""
    context.configure(
        url=url_do_banco(),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def executar_online():
    motor = create_engine(url_do_banco(), poolclass=pool.NullPool)

    with motor.connect() as conexao:
        context.configure(connection=conexao)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    executar_offline()
else:
    executar_online()
