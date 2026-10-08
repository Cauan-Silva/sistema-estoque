import psycopg2

from backend.database import conectar


def cadastrar_fornecedor(
    nome: str,
    cpf_cnpj: str | None = None,
    contato: str | None = None,
    telefone: str | None = None,
    email: str | None = None,
    site: str | None = None
):
    conexao = conectar()

    if conexao is None:
        return None

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            INSERT INTO fornecedores (
                nome,
                cpf_cnpj,
                contato,
                telefone,
                email,
                site
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING
                id,
                nome,
                cpf_cnpj,
                contato,
                telefone,
                email,
                site,
                ativo,
                data_criacao;
            """,
            (
                nome,
                cpf_cnpj,
                contato,
                telefone,
                email,
                site
            )
        )

        fornecedor = cursor.fetchone()

        conexao.commit()

        cursor.close()
        conexao.close()

        return fornecedor

    except psycopg2.Error:
        conexao.rollback()
        conexao.close()

        return None


def buscar_fornecedor(fornecedor_id: int):
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
                cpf_cnpj,
                contato,
                telefone,
                email,
                site,
                ativo,
                data_criacao
            FROM fornecedores
            WHERE id = %s;
            """,
            (fornecedor_id,)
        )

        fornecedor = cursor.fetchone()

        cursor.close()
        conexao.close()

        return fornecedor

    except psycopg2.Error:
        conexao.close()
        return None


def listar_fornecedores(ativo: bool | None = None):
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
                cpf_cnpj,
                contato,
                telefone,
                email,
                site,
                ativo,
                data_criacao
            FROM fornecedores
            WHERE (%s IS NULL OR ativo = %s)
            ORDER BY nome;
            """,
            (ativo, ativo)
        )

        fornecedores = cursor.fetchall()

        cursor.close()
        conexao.close()

        return fornecedores

    except psycopg2.Error:
        conexao.close()
        return []


def atualizar_fornecedor(
    fornecedor_id: int,
    nome: str,
    cpf_cnpj: str | None = None,
    contato: str | None = None,
    telefone: str | None = None,
    email: str | None = None,
    site: str | None = None
):
    conexao = conectar()

    if conexao is None:
        return None

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            UPDATE fornecedores
            SET
                nome = %s,
                cpf_cnpj = %s,
                contato = %s,
                telefone = %s,
                email = %s,
                site = %s
            WHERE id = %s
            RETURNING
                id,
                nome,
                cpf_cnpj,
                contato,
                telefone,
                email,
                site,
                ativo,
                data_criacao;
            """,
            (
                nome,
                cpf_cnpj,
                contato,
                telefone,
                email,
                site,
                fornecedor_id
            )
        )

        fornecedor = cursor.fetchone()

        conexao.commit()

        cursor.close()
        conexao.close()

        return fornecedor

    except psycopg2.Error:
        conexao.rollback()
        conexao.close()

        return None


def alterar_status_fornecedor(
    fornecedor_id: int,
    ativo: bool
):
    conexao = conectar()

    if conexao is None:
        return None

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            UPDATE fornecedores
            SET ativo = %s
            WHERE id = %s
            RETURNING
                id,
                nome,
                cpf_cnpj,
                contato,
                telefone,
                email,
                site,
                ativo,
                data_criacao;
            """,
            (
                ativo,
                fornecedor_id
            )
        )

        fornecedor = cursor.fetchone()

        conexao.commit()

        cursor.close()
        conexao.close()

        return fornecedor

    except psycopg2.Error:
        conexao.rollback()
        conexao.close()

        return None
