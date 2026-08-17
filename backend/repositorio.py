import psycopg2

from backend.database import conectar
from backend.produto import Produto


def cadastrar_produto(nome, categoria, quantidade, preco):
    conexao = conectar()

    if conexao is None:
        return None

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            INSERT INTO produtos (
                nome,
                categoria,
                quantidade,
                preco
            )
            VALUES (%s, %s, %s, %s)
            RETURNING id;
            """,
            (
                nome,
                categoria,
                quantidade,
                preco
            )
        )

        id_produto = cursor.fetchone()[0]

        conexao.commit()

        cursor.close()
        conexao.close()

        return buscar_produto_por_id(id_produto)

    except psycopg2.Error as erro:
        conexao.rollback()
        conexao.close()

        print(f"Erro ao cadastrar produto: {erro}")

        return None


def listar_produtos():
    conexao = conectar()

    if conexao is None:
        return []

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            SELECT
                id,
                nome,
                categoria,
                quantidade,
                preco
            FROM produtos
            ORDER BY id;
            """
        )

        registros = cursor.fetchall()

        produtos = []

        for registro in registros:
            produtos.append(
                Produto(
                    registro[0],
                    registro[1],
                    registro[2],
                    registro[3],
                    float(registro[4])
                )
            )

        cursor.close()
        conexao.close()

        return produtos

    except psycopg2.Error as erro:
        conexao.close()

        print(f"Erro ao listar produtos: {erro}")

        return []


def buscar_produto_por_id(id_produto):
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
                categoria,
                quantidade,
                preco
            FROM produtos
            WHERE id = %s;
            """,
            (id_produto,)
        )

        registro = cursor.fetchone()

        cursor.close()
        conexao.close()

        if registro is None:
            return None

        return Produto(
            registro[0],
            registro[1],
            registro[2],
            registro[3],
            float(registro[4])
        )

    except psycopg2.Error as erro:
        conexao.close()

        print(f"Erro ao buscar produto: {erro}")

        return None


def atualizar_produto(
    id_produto,
    nome,
    categoria,
    quantidade,
    preco
):
    conexao = conectar()

    if conexao is None:
        return None

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            UPDATE produtos
            SET
                nome = %s,
                categoria = %s,
                quantidade = %s,
                preco = %s
            WHERE id = %s
            RETURNING id;
            """,
            (
                nome,
                categoria,
                quantidade,
                preco,
                id_produto
            )
        )

        registro = cursor.fetchone()

        conexao.commit()

        cursor.close()
        conexao.close()

        if registro is None:
            return None

        return buscar_produto_por_id(id_produto)

    except psycopg2.Error as erro:
        conexao.rollback()
        conexao.close()

        print(f"Erro ao atualizar produto: {erro}")

        return None


def excluir_produto(id_produto):
    conexao = conectar()

    if conexao is None:
        return False

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            DELETE FROM produtos
            WHERE id = %s;
            """,
            (id_produto,)
        )

        excluido = cursor.rowcount > 0

        conexao.commit()

        cursor.close()
        conexao.close()

        return excluido

    except psycopg2.Error as erro:
        conexao.rollback()
        conexao.close()

        print(f"Erro ao excluir produto: {erro}")

        return False