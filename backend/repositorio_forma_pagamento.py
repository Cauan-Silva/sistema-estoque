import psycopg2

from backend.database import conectar


COLUNAS = """
    id,
    codigo,
    titulo,
    tipo,
    parcelas,
    intervalo_dias,
    ativo
"""

ORDENACOES = {
    "codigo": "codigo",
    "titulo": "titulo",
    "tipo": "tipo",
}


def _montar(registro):
    return {
        "id": registro[0],
        "codigo": registro[1],
        "titulo": registro[2],
        "tipo": registro[3],
        "parcelas": registro[4],
        "intervalo_dias": registro[5],
        "ativo": registro[6],
    }


def descrever(forma) -> str:
    return f"{forma['codigo']} - {forma['titulo']}"


def listar_formas_pagamento(
    busca: str | None = None,
    tipo: str | None = None,
    ativo: bool | None = None,
    ordem: str = "codigo",
    decrescente: bool = False,
    pagina: int = 1,
    tamanho: int = 10
):
    conexao = conectar()

    if conexao is None:
        return None

    condicoes = []
    parametros = []

    if busca:
        condicoes.append("(codigo ILIKE %s OR titulo ILIKE %s)")
        parametros.extend([f"%{busca}%", f"%{busca}%"])

    if tipo is not None:
        condicoes.append("tipo = %s")
        parametros.append(tipo)

    if ativo is not None:
        condicoes.append("ativo = %s")
        parametros.append(ativo)

    clausula = " WHERE " + " AND ".join(condicoes) if condicoes else ""
    coluna = ORDENACOES.get(ordem, "codigo")
    direcao = "DESC" if decrescente else "ASC"

    try:
        cursor = conexao.cursor()

        cursor.execute(
            f"SELECT COUNT(*) FROM formas_pagamento{clausula};",
            tuple(parametros)
        )

        total = cursor.fetchone()[0]

        cursor.execute(
            f"""
            SELECT {COLUNAS}
            FROM formas_pagamento
            {clausula}
            ORDER BY {coluna} {direcao}, codigo {direcao}
            LIMIT %s
            OFFSET %s;
            """,
            (*parametros, tamanho, (pagina - 1) * tamanho)
        )

        itens = [_montar(registro) for registro in cursor.fetchall()]

        cursor.close()
        conexao.close()

        return {
            "total": total,
            "pagina": pagina,
            "tamanho": tamanho,
            "itens": itens,
        }

    except psycopg2.Error as erro:
        conexao.close()

        print(f"Erro ao listar formas de pagamento: {erro}")

        return None


def buscar_forma_pagamento(forma_id: int):
    conexao = conectar()

    if conexao is None:
        return None

    try:
        cursor = conexao.cursor()

        cursor.execute(
            f"SELECT {COLUNAS} FROM formas_pagamento WHERE id = %s;",
            (forma_id,)
        )

        registro = cursor.fetchone()

        cursor.close()
        conexao.close()

        return _montar(registro) if registro else None

    except psycopg2.Error as erro:
        conexao.close()

        print(f"Erro ao buscar forma de pagamento: {erro}")

        return None


def _gravar(sql: str, parametros):
    conexao = conectar()

    if conexao is None:
        return None, "erro_conexao"

    try:
        cursor = conexao.cursor()

        cursor.execute(sql, parametros)

        registro = cursor.fetchone()

        conexao.commit()

        cursor.close()
        conexao.close()

        if registro is None:
            return None, "forma_nao_encontrada"

        return _montar(registro), None

    except psycopg2.errors.UniqueViolation:
        conexao.rollback()
        conexao.close()

        return None, "codigo_duplicado"

    except psycopg2.Error as erro:
        conexao.rollback()
        conexao.close()

        print(f"Erro ao gravar forma de pagamento: {erro}")

        return None, "erro_banco"


def cadastrar_forma_pagamento(codigo, titulo, tipo, parcelas, intervalo_dias):
    return _gravar(
        f"""
        INSERT INTO formas_pagamento (
            codigo,
            titulo,
            tipo,
            parcelas,
            intervalo_dias
        )
        VALUES (%s, %s, %s, %s, %s)
        RETURNING {COLUNAS};
        """,
        (codigo, titulo, tipo, parcelas, intervalo_dias)
    )


def atualizar_forma_pagamento(
    forma_id,
    codigo,
    titulo,
    tipo,
    parcelas,
    intervalo_dias
):
    return _gravar(
        f"""
        UPDATE formas_pagamento
        SET
            codigo = %s,
            titulo = %s,
            tipo = %s,
            parcelas = %s,
            intervalo_dias = %s
        WHERE id = %s
        RETURNING {COLUNAS};
        """,
        (codigo, titulo, tipo, parcelas, intervalo_dias, forma_id)
    )


def alterar_status_forma_pagamento(forma_id, ativo):
    return _gravar(
        f"""
        UPDATE formas_pagamento
        SET ativo = %s
        WHERE id = %s
        RETURNING {COLUNAS};
        """,
        (ativo, forma_id)
    )
