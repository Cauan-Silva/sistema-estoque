import psycopg2

from backend.database import conectar


def obter_resumo_estoque(limite_estoque=5):
    conexao = conectar()

    if conexao is None:
        return None

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM produtos;
            """
        )

        total_produtos = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM categorias;
            """
        )

        total_categorias = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COALESCE(
                SUM(quantidade),
                0
            )
            FROM produtos;
            """
        )

        unidades_em_estoque = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM produtos
            WHERE quantidade <= %s;
            """,
            (limite_estoque,)
        )

        produtos_estoque_baixo = (
            cursor.fetchone()[0]
        )

        cursor.execute(
            """
            SELECT COALESCE(
                SUM(quantidade * preco),
                0
            )
            FROM produtos;
            """
        )

        valor_total_estoque = float(
            cursor.fetchone()[0]
        )

        cursor.execute(
            """
            SELECT COALESCE(
                SUM(quantidade),
                0
            )
            FROM movimentacoes
            WHERE tipo = 'ENTRADA';
            """
        )

        total_entradas = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COALESCE(
                SUM(quantidade),
                0
            )
            FROM movimentacoes
            WHERE tipo = 'SAIDA';
            """
        )

        total_saidas = cursor.fetchone()[0]

        cursor.close()
        conexao.close()

        return {
            "total_produtos": total_produtos,
            "total_categorias": total_categorias,
            "unidades_em_estoque": unidades_em_estoque,
            "produtos_estoque_baixo": (
                produtos_estoque_baixo
            ),
            "valor_total_estoque": (
                valor_total_estoque
            ),
            "total_entradas": total_entradas,
            "total_saidas": total_saidas
        }

    except psycopg2.Error as erro:
        conexao.close()

        print(
            f"Erro ao gerar resumo do estoque: {erro}"
        )

        return None


def listar_produtos_maior_valor(
    limite=10
):
    conexao = conectar()

    if conexao is None:
        return []

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            SELECT
                p.id,
                p.nome,
                c.nome,
                p.quantidade,
                p.preco,
                (
                    p.quantidade * p.preco
                ) AS valor_estoque
            FROM produtos p
            INNER JOIN categorias c
                ON c.id = p.categoria_id
            ORDER BY
                valor_estoque DESC,
                p.id ASC
            LIMIT %s;
            """,
            (limite,)
        )

        registros = cursor.fetchall()

        produtos = []

        for registro in registros:
            produtos.append(
                {
                    "id": registro[0],
                    "nome": registro[1],
                    "categoria": registro[2],
                    "quantidade": registro[3],
                    "preco": float(
                        registro[4]
                    ),
                    "valor_estoque": float(
                        registro[5]
                    )
                }
            )

        cursor.close()
        conexao.close()

        return produtos

    except psycopg2.Error as erro:
        conexao.close()

        print(
            "Erro ao gerar relatório de "
            f"valor do estoque: {erro}"
        )

        return []