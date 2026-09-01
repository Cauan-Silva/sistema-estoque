import psycopg2

from backend.database import conectar


def registrar_movimentacao(
    produto_id,
    tipo,
    quantidade
):
    conexao = conectar()

    if conexao is None:
        return None, "erro_conexao"

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            SELECT
                nome,
                quantidade
            FROM produtos
            WHERE id = %s
            FOR UPDATE;
            """,
            (produto_id,)
        )

        produto = cursor.fetchone()

        if produto is None:
            conexao.rollback()
            cursor.close()
            conexao.close()

            return None, "produto_nao_encontrado"

        estoque_atual = produto[1]

        if tipo == "ENTRADA":
            novo_estoque = (
                estoque_atual + quantidade
            )

        elif tipo == "SAIDA":
            if quantidade > estoque_atual:
                conexao.rollback()
                cursor.close()
                conexao.close()

                return None, "estoque_insuficiente"

            novo_estoque = (
                estoque_atual - quantidade
            )

        else:
            conexao.rollback()
            cursor.close()
            conexao.close()

            return None, "tipo_invalido"

        cursor.execute(
            """
            UPDATE produtos
            SET quantidade = %s
            WHERE id = %s;
            """,
            (
                novo_estoque,
                produto_id
            )
        )

        cursor.execute(
            """
            INSERT INTO movimentacoes (
                produto_id,
                tipo,
                quantidade
            )
            VALUES (%s, %s, %s)
            RETURNING
                id,
                data_movimentacao;
            """,
            (
                produto_id,
                tipo,
                quantidade
            )
        )

        registro = cursor.fetchone()

        conexao.commit()

        movimentacao = {
            "id": registro[0],
            "produto_id": produto_id,
            "produto_nome": produto[0],
            "tipo": tipo,
            "quantidade": quantidade,
            "data_movimentacao": registro[1]
        }

        cursor.close()
        conexao.close()

        return movimentacao, None

    except psycopg2.Error as erro:
        conexao.rollback()
        conexao.close()

        print(
            f"Erro ao registrar movimentação: {erro}"
        )

        return None, "erro_banco"


def listar_movimentacoes(
    produto_id=None,
    tipo=None,
    data_inicio=None,
    data_fim=None
):
    conexao = conectar()

    if conexao is None:
        return []

    try:
        cursor = conexao.cursor()

        consulta = """
            SELECT
                m.id,
                m.produto_id,
                p.nome,
                m.tipo,
                m.quantidade,
                m.data_movimentacao
            FROM movimentacoes m
            INNER JOIN produtos p
                ON p.id = m.produto_id
        """

        condicoes = []
        parametros = []

        if produto_id is not None:
            condicoes.append(
                "m.produto_id = %s"
            )
            parametros.append(
                produto_id
            )

        if tipo is not None:
            condicoes.append(
                "m.tipo = %s"
            )
            parametros.append(
                tipo
            )

        if data_inicio is not None:
            condicoes.append(
                "m.data_movimentacao >= %s"
            )
            parametros.append(
                data_inicio
            )

        if data_fim is not None:
            condicoes.append(
                "m.data_movimentacao <= %s"
            )
            parametros.append(
                data_fim
            )

        if condicoes:
            consulta += (
                " WHERE "
                + " AND ".join(condicoes)
            )

        consulta += """
            ORDER BY
                m.data_movimentacao DESC,
                m.id DESC;
        """

        cursor.execute(
            consulta,
            tuple(parametros)
        )

        registros = cursor.fetchall()

        movimentacoes = []

        for registro in registros:
            movimentacoes.append(
                {
                    "id": registro[0],
                    "produto_id": registro[1],
                    "produto_nome": registro[2],
                    "tipo": registro[3],
                    "quantidade": registro[4],
                    "data_movimentacao": registro[5]
                }
            )

        cursor.close()
        conexao.close()

        return movimentacoes

    except psycopg2.Error as erro:
        conexao.close()

        print(
            f"Erro ao listar movimentações: {erro}"
        )

        return []


def buscar_movimentacao_por_id(
    id_movimentacao
):
    conexao = conectar()

    if conexao is None:
        return None

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            SELECT
                m.id,
                m.produto_id,
                p.nome,
                m.tipo,
                m.quantidade,
                m.data_movimentacao
            FROM movimentacoes m
            INNER JOIN produtos p
                ON p.id = m.produto_id
            WHERE m.id = %s;
            """,
            (id_movimentacao,)
        )

        registro = cursor.fetchone()

        cursor.close()
        conexao.close()

        if registro is None:
            return None

        return {
            "id": registro[0],
            "produto_id": registro[1],
            "produto_nome": registro[2],
            "tipo": registro[3],
            "quantidade": registro[4],
            "data_movimentacao": registro[5]
        }

    except psycopg2.Error as erro:
        conexao.close()

        print(
            f"Erro ao buscar movimentação: {erro}"
        )

        return None