import psycopg2

from backend.database import conectar
from backend.produto import Produto


def cadastrar_produto(
    nome,
    categoria_id,
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
            SELECT nome
            FROM categorias
            WHERE id = %s;
            """,
            (categoria_id,)
        )

        categoria = cursor.fetchone()

        if categoria is None:
            cursor.close()
            conexao.close()
            return None

        nome_categoria = categoria[0]

        cursor.execute(
            """
            INSERT INTO produtos (
                nome,
                categoria,
                categoria_id,
                quantidade,
                preco
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (
                nome,
                nome_categoria,
                categoria_id,
                quantidade,
                preco
            )
        )

        id_produto = cursor.fetchone()[0]

        conexao.commit()

        cursor.close()
        conexao.close()

        return buscar_produto_por_id(
            id_produto
        )

    except psycopg2.Error as erro:
        conexao.rollback()
        conexao.close()

        print(
            f"Erro ao cadastrar produto: {erro}"
        )

        return None


def listar_produtos(
    busca=None,
    categoria_id=None,
    estoque_baixo=False,
    limite_estoque=5
):
    conexao = conectar()

    if conexao is None:
        return []

    try:
        cursor = conexao.cursor()

        consulta = """
            SELECT
                p.id,
                p.nome,
                p.categoria_id,
                c.nome,
                p.quantidade,
                p.preco
            FROM produtos p
            LEFT JOIN categorias c
                ON c.id = p.categoria_id
        """

        condicoes = []
        parametros = []

        if busca:
            condicoes.append(
                "p.nome ILIKE %s"
            )

            parametros.append(
                f"%{busca}%"
            )

        if categoria_id is not None:
            condicoes.append(
                "p.categoria_id = %s"
            )

            parametros.append(
                categoria_id
            )

        if estoque_baixo:
            condicoes.append(
                "p.quantidade <= %s"
            )

            parametros.append(
                limite_estoque
            )

        if condicoes:
            consulta += (
                " WHERE "
                + " AND ".join(condicoes)
            )

        consulta += " ORDER BY p.id;"

        cursor.execute(
            consulta,
            tuple(parametros)
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
                    registro[4],
                    float(registro[5])
                )
            )

        cursor.close()
        conexao.close()

        return produtos

    except psycopg2.Error as erro:
        conexao.close()

        print(
            f"Erro ao listar produtos: {erro}"
        )

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
                p.id,
                p.nome,
                p.categoria_id,
                c.nome,
                p.quantidade,
                p.preco
            FROM produtos p
            LEFT JOIN categorias c
                ON c.id = p.categoria_id
            WHERE p.id = %s;
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
            registro[4],
            float(registro[5])
        )

    except psycopg2.Error as erro:
        conexao.close()

        print(
            f"Erro ao buscar produto: {erro}"
        )

        return None


def atualizar_produto(
    id_produto,
    nome,
    categoria_id,
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
            SELECT nome
            FROM categorias
            WHERE id = %s;
            """,
            (categoria_id,)
        )

        categoria = cursor.fetchone()

        if categoria is None:
            cursor.close()
            conexao.close()
            return None

        nome_categoria = categoria[0]

        cursor.execute(
            """
            UPDATE produtos
            SET
                nome = %s,
                categoria = %s,
                categoria_id = %s,
                quantidade = %s,
                preco = %s
            WHERE id = %s
            RETURNING id;
            """,
            (
                nome,
                nome_categoria,
                categoria_id,
                quantidade,
                preco,
                id_produto
            )
        )

        registro = cursor.fetchone()

        if registro is None:
            conexao.rollback()

            cursor.close()
            conexao.close()

            return None

        conexao.commit()

        cursor.close()
        conexao.close()

        return buscar_produto_por_id(
            id_produto
        )

    except psycopg2.Error as erro:
        conexao.rollback()
        conexao.close()

        print(
            f"Erro ao atualizar produto: {erro}"
        )

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

        print(
            f"Erro ao excluir produto: {erro}"
        )

        return False