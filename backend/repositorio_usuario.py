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


def verificar_senha(
    senha: str,
    senha_hash: str
) -> bool:
    return bcrypt.checkpw(
        senha.encode("utf-8"),
        senha_hash.encode("utf-8")
    )


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
                senha_hash,
                perfil
            )
            SELECT
                %s,
                %s,
                %s,
                CASE
                    WHEN EXISTS (SELECT 1 FROM usuarios) THEN 'CONSULTA'
                    ELSE 'ADMINISTRADOR'
                END
            RETURNING
                id,
                nome,
                email,
                ativo,
                data_criacao,
                perfil;
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
                data_criacao,
                perfil
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


def buscar_usuario_por_id(usuario_id: int):
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
                data_criacao,
                perfil
            FROM usuarios
            WHERE id = %s;
            """,
            (usuario_id,)
        )

        usuario = cursor.fetchone()

        cursor.close()
        conexao.close()

        return usuario

    except psycopg2.Error:
        conexao.close()
        return None


COLUNAS_PUBLICAS = """
    id,
    nome,
    email,
    ativo,
    data_criacao,
    perfil
"""


def _usuario_publico(registro):
    return {
        "id": registro[0],
        "nome": registro[1],
        "email": registro[2],
        "ativo": registro[3],
        "data_criacao": registro[4],
        "perfil": registro[5],
    }


def listar_usuarios():
    conexao = conectar()

    if conexao is None:
        return None

    try:
        cursor = conexao.cursor()

        cursor.execute(
            f"SELECT {COLUNAS_PUBLICAS} FROM usuarios ORDER BY nome, id;"
        )

        usuarios = [_usuario_publico(r) for r in cursor.fetchall()]

        cursor.close()
        conexao.close()

        return usuarios

    except psycopg2.Error:
        conexao.close()
        return None


def atualizar_acesso_usuario(
    usuario_id: int,
    perfil: str | None,
    ativo: bool | None
):
    conexao = conectar()

    if conexao is None:
        return None, "erro_conexao"

    try:
        cursor = conexao.cursor()

        cursor.execute(
            f"""
            UPDATE usuarios
            SET
                perfil = COALESCE(%s, perfil),
                ativo = COALESCE(%s, ativo)
            WHERE id = %s
            RETURNING {COLUNAS_PUBLICAS};
            """,
            (perfil, ativo, usuario_id)
        )

        registro = cursor.fetchone()

        conexao.commit()

        cursor.close()
        conexao.close()

        if registro is None:
            return None, "usuario_nao_encontrado"

        return _usuario_publico(registro), None

    except psycopg2.Error:
        conexao.rollback()
        conexao.close()

        return None, "erro_banco"
