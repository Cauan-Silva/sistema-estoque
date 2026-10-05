import bcrypt
import psycopg2

from backend.database import conectar


def gerar_hash_senha(senha: str) -> str:
    senha_bytes = senha.encode("utf-8")

    hash_bytes = bcrypt.hashpw(
        senha_bytes,
        bcrypt.gensalt()
    )

    return hash_bytes.decode("utf-8")


def cadastrar_usuario(nome: str, email: str, senha: str):
    conexao = conectar()

    if conexao is None:
        return None, "erro_conexao"

    try:
        cursor = conexao.cursor()

        senha_hash = gerar_hash_senha(senha)

        cursor.execute(
            """
            INSERT INTO usuarios (
                nome,
                email,
                senha_hash
            )
            VALUES (%s, %s, %s)
            RETURNING
                id,
                nome,
                email,
                ativo,
                data_criacao;
            """,
            (
                nome,
                email.lower(),
                senha_hash
            )
        )

        usuario = cursor.fetchone()

        conexao.commit()

        cursor.close()
        conexao.close()

        return usuario, None

    except psycopg2.errors.UniqueViolation:
        conexao.rollback()
        conexao.close()

        return None, "email_duplicado"

    except psycopg2.Error:
        conexao.rollback()
        conexao.close()

        return None, "erro_banco"


def buscar_usuario_por_email(email: str):
    conexao = conectar()

    if conexao is None:
        return None

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            SELECT
                id,
                nome,
                email,
                senha_hash,
                ativo,
                data_criacao
            FROM usuarios
            WHERE email = %s;
            """,
            (email.lower(),)
        )

        usuario = cursor.fetchone()

        cursor.close()
        conexao.close()

        return usuario

    except psycopg2.Error:
        conexao.close()
        return None