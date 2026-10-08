import psycopg2

from backend.database import conectar


STATUS_EDITAVEIS = ("ABERTA",)


def _buscar_itens(cursor, solicitacao_id: int):
    cursor.execute(
        """
        SELECT
            i.id,
            i.produto_id,
            p.nome,
            i.quantidade
        FROM itens_solicitacao_compra i
        JOIN produtos p
            ON p.id = i.produto_id
        WHERE i.solicitacao_id = %s
        ORDER BY i.id;
        """,
        (solicitacao_id,)
    )

    return [
        {
            "id": registro[0],
            "produto_id": registro[1],
            "produto": registro[2],
            "quantidade": registro[3]
        }
        for registro in cursor.fetchall()
    ]


def _montar_solicitacao(cursor, registro):
    return {
        "id": registro[0],
        "solicitante_id": registro[1],
        "solicitante": registro[2],
        "status": registro[3],
        "observacao": registro[4],
        "data_criacao": registro[5],
        "data_atualizacao": registro[6],
        "itens": _buscar_itens(cursor, registro[0])
    }


CONSULTA_SOLICITACAO = """
    SELECT
        s.id,
        s.solicitante_id,
        u.nome,
        s.status,
        s.observacao,
        s.data_criacao,
        s.data_atualizacao
    FROM solicitacoes_compra s
    JOIN usuarios u
        ON u.id = s.solicitante_id
"""


def _produtos_inexistentes(cursor, produto_ids: list[int]):
    cursor.execute(
        """
        SELECT id
        FROM produtos
        WHERE id = ANY(%s);
        """,
        (produto_ids,)
    )

    encontrados = {registro[0] for registro in cursor.fetchall()}

    return [
        produto_id
        for produto_id in produto_ids
        if produto_id not in encontrados
    ]


def _inserir_itens(cursor, solicitacao_id: int, itens):
    for item in itens:
        cursor.execute(
            """
            INSERT INTO itens_solicitacao_compra (
                solicitacao_id,
                produto_id,
                quantidade
            )
            VALUES (%s, %s, %s);
            """,
            (
                solicitacao_id,
                item["produto_id"],
                item["quantidade"]
            )
        )


def criar_solicitacao(
    solicitante_id: int,
    observacao: str | None,
    itens
):
    conexao = conectar()

    if conexao is None:
        return None, "erro_conexao"

    try:
        cursor = conexao.cursor()

        inexistentes = _produtos_inexistentes(
            cursor,
            [item["produto_id"] for item in itens]
        )

        if inexistentes:
            conexao.rollback()
            cursor.close()
            conexao.close()

            return None, "produto_nao_encontrado"

        cursor.execute(
            """
            INSERT INTO solicitacoes_compra (
                solicitante_id,
                observacao
            )
            VALUES (%s, %s)
            RETURNING id;
            """,
            (
                solicitante_id,
                observacao
            )
        )

        solicitacao_id = cursor.fetchone()[0]

        _inserir_itens(cursor, solicitacao_id, itens)

        conexao.commit()

        cursor.close()
        conexao.close()

        return buscar_solicitacao(solicitacao_id), None

    except psycopg2.Error as erro:
        conexao.rollback()
        conexao.close()

        print(f"Erro ao criar solicitação de compra: {erro}")

        return None, "erro_banco"


def buscar_solicitacao(solicitacao_id: int):
    conexao = conectar()

    if conexao is None:
        return None

    try:
        cursor = conexao.cursor()

        cursor.execute(
            CONSULTA_SOLICITACAO + " WHERE s.id = %s;",
            (solicitacao_id,)
        )

        registro = cursor.fetchone()

        solicitacao = (
            _montar_solicitacao(cursor, registro)
            if registro is not None
            else None
        )

        cursor.close()
        conexao.close()

        return solicitacao

    except psycopg2.Error as erro:
        conexao.close()

        print(f"Erro ao buscar solicitação de compra: {erro}")

        return None


def listar_solicitacoes(
    status: str | None = None,
    solicitante_id: int | None = None,
    pagina: int = 1,
    tamanho: int = 10
):
    conexao = conectar()

    if conexao is None:
        return []

    try:
        cursor = conexao.cursor()

        condicoes = []
        parametros = []

        if status is not None:
            condicoes.append("s.status = %s")
            parametros.append(status)

        if solicitante_id is not None:
            condicoes.append("s.solicitante_id = %s")
            parametros.append(solicitante_id)

        consulta = CONSULTA_SOLICITACAO

        if condicoes:
            consulta += " WHERE " + " AND ".join(condicoes)

        consulta += """
            ORDER BY s.id DESC
            LIMIT %s
            OFFSET %s;
        """

        parametros.append(tamanho)
        parametros.append((pagina - 1) * tamanho)

        cursor.execute(consulta, tuple(parametros))

        registros = cursor.fetchall()

        solicitacoes = [
            _montar_solicitacao(cursor, registro)
            for registro in registros
        ]

        cursor.close()
        conexao.close()

        return solicitacoes

    except psycopg2.Error as erro:
        conexao.close()

        print(f"Erro ao listar solicitações de compra: {erro}")

        return []


def _status_para_alteracao(cursor, solicitacao_id: int):
    cursor.execute(
        """
        SELECT status
        FROM solicitacoes_compra
        WHERE id = %s
        FOR UPDATE;
        """,
        (solicitacao_id,)
    )

    registro = cursor.fetchone()

    if registro is None:
        return None, "solicitacao_nao_encontrada"

    if registro[0] not in STATUS_EDITAVEIS:
        return None, "status_nao_permite_alteracao"

    return registro[0], None


def atualizar_solicitacao(
    solicitacao_id: int,
    observacao: str | None,
    itens
):
    conexao = conectar()

    if conexao is None:
        return None, "erro_conexao"

    try:
        cursor = conexao.cursor()

        _, erro = _status_para_alteracao(cursor, solicitacao_id)

        if erro is not None:
            conexao.rollback()
            cursor.close()
            conexao.close()

            return None, erro

        inexistentes = _produtos_inexistentes(
            cursor,
            [item["produto_id"] for item in itens]
        )

        if inexistentes:
            conexao.rollback()
            cursor.close()
            conexao.close()

            return None, "produto_nao_encontrado"

        cursor.execute(
            """
            UPDATE solicitacoes_compra
            SET
                observacao = %s,
                data_atualizacao = CURRENT_TIMESTAMP
            WHERE id = %s;
            """,
            (
                observacao,
                solicitacao_id
            )
        )

        cursor.execute(
            """
            DELETE FROM itens_solicitacao_compra
            WHERE solicitacao_id = %s;
            """,
            (solicitacao_id,)
        )

        _inserir_itens(cursor, solicitacao_id, itens)

        conexao.commit()

        cursor.close()
        conexao.close()

        return buscar_solicitacao(solicitacao_id), None

    except psycopg2.Error as erro:
        conexao.rollback()
        conexao.close()

        print(f"Erro ao atualizar solicitação de compra: {erro}")

        return None, "erro_banco"


def cancelar_solicitacao(solicitacao_id: int):
    conexao = conectar()

    if conexao is None:
        return None, "erro_conexao"

    try:
        cursor = conexao.cursor()

        _, erro = _status_para_alteracao(cursor, solicitacao_id)

        if erro is not None:
            conexao.rollback()
            cursor.close()
            conexao.close()

            return None, erro

        cursor.execute(
            """
            UPDATE solicitacoes_compra
            SET
                status = 'CANCELADA',
                data_atualizacao = CURRENT_TIMESTAMP
            WHERE id = %s;
            """,
            (solicitacao_id,)
        )

        conexao.commit()

        cursor.close()
        conexao.close()

        return buscar_solicitacao(solicitacao_id), None

    except psycopg2.Error as erro:
        conexao.rollback()
        conexao.close()

        print(f"Erro ao cancelar solicitação de compra: {erro}")

        return None, "erro_banco"
