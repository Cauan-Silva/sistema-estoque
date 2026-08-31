from backend.database import conectar


def cadastrar_categoria(nome):
    conexao = conectar()

    if conexao is None:
        return None

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            INSERT INTO categorias (nome)
            VALUES (%s)
            RETURNING id;
            """,
            (nome,)
        )

        categoria_id = cursor.fetchone()[0]

        conexao.commit()

        cursor.close()
        conexao.close()

        return {
            "id": categoria_id,
            "nome": nome
        }

    except Exception:
        conexao.rollback()
        conexao.close()
        raise


def listar_categorias():
    conexao = conectar()

    if conexao is None:
        return []

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            SELECT
                id,
                nome
            FROM categorias
            ORDER BY nome;
            """
        )

        registros = cursor.fetchall()

        cursor.close()
        conexao.close()

        return [
            {
                "id": registro[0],
                "nome": registro[1]
            }
            for registro in registros
        ]

    except Exception:
        conexao.close()
        raise


def buscar_categoria(id_categoria):
    conexao = conectar()

    if conexao is None:
        return None

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            SELECT
                id,
                nome
            FROM categorias
            WHERE id = %s;
            """,
            (id_categoria,)
        )

        registro = cursor.fetchone()

        cursor.close()
        conexao.close()

        if registro is None:
            return None

        return {
            "id": registro[0],
            "nome": registro[1]
        }

    except Exception:
        conexao.close()
        raise


def editar_categoria(id_categoria, nome):
    conexao = conectar()

    if conexao is None:
        return None

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            UPDATE categorias
            SET nome = %s
            WHERE id = %s
            RETURNING id, nome;
            """,
            (
                nome,
                id_categoria
            )
        )

        registro = cursor.fetchone()

        if registro is None:
            conexao.rollback()

            cursor.close()
            conexao.close()

            return None

        cursor.execute(
            """
            UPDATE produtos
            SET categoria = %s
            WHERE categoria_id = %s;
            """,
            (
                nome,
                id_categoria
            )
        )

        conexao.commit()

        cursor.close()
        conexao.close()

        return {
            "id": registro[0],
            "nome": registro[1]
        }

    except Exception:
        conexao.rollback()
        conexao.close()
        raise


def excluir_categoria(id_categoria):
    conexao = conectar()

    if conexao is None:
        return False

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            DELETE FROM categorias
            WHERE id = %s
            RETURNING id;
            """,
            (id_categoria,)
        )

        registro = cursor.fetchone()

        if registro is None:
            conexao.rollback()

            cursor.close()
            conexao.close()

            return False

        conexao.commit()

        cursor.close()
        conexao.close()

        return True

    except Exception:
        conexao.rollback()
        conexao.close()
        raise