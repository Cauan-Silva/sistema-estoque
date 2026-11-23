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


# Chave fixa do advisory lock que serializa os cadastros de usuário. Assim,
# duas requisições simultâneas num banco vazio não viram ambas administrador.
TRAVA_CADASTRO_USUARIO = 72_640_001


def existe_usuario() -> bool | None:
    conexao = conectar()

    if conexao is None:
        return None

    try:
        cursor = conexao.cursor()
        cursor.execute("SELECT EXISTS (SELECT 1 FROM usuarios);")
        existe = cursor.fetchone()[0]
        cursor.close()
        conexao.close()

        return existe

    except psycopg2.Error:
        conexao.close()
        return None


def cadastrar_usuario(
    nome: str,
    email: str,
    senha: str,
    perfil: str | None = None,
    apenas_primeiro: bool = False
):
    """Cadastra um usuário.

    O primeiro usuário do sistema é sempre ADMINISTRADOR; os demais recebem
    `perfil` (padrão CONSULTA). Com `apenas_primeiro=True`, só cadastra se
    ainda não houver nenhum usuário (devolve o erro "ja_existem_usuarios").
    A verificação e o INSERT ocorrem na mesma transação, sob um advisory lock.
    """
    conexao = conectar()

    if conexao is None:
        return None, "erro_conexao"

    try:
        cursor = conexao.cursor()

        senha_hash = gerar_hash_senha(senha)

        cursor.execute(
            "SELECT pg_advisory_xact_lock(%s);",
            (TRAVA_CADASTRO_USUARIO,)
        )
        cursor.execute("SELECT EXISTS (SELECT 1 FROM usuarios);")
        ja_existe = cursor.fetchone()[0]

        if ja_existe and apenas_primeiro:
            conexao.rollback()
            cursor.close()
            conexao.close()

            return None, "ja_existem_usuarios"

        perfil_final = (
            (perfil or "CONSULTA") if ja_existe else "ADMINISTRADOR"
        )

        cursor.execute(
            """
            INSERT INTO usuarios (
                nome,
                email,
                senha_hash,
                perfil
            )
            VALUES (%s, %s, %s, %s)
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
                senha_hash,
                perfil_final
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
