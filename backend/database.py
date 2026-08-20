import os

import psycopg2
from dotenv import load_dotenv


load_dotenv()


def conectar():
    try:
        conexao = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )

        return conexao

    except psycopg2.Error as erro:
        print(f"Erro ao conectar ao banco de dados: {erro}")
        return None


def criar_tabela():
    conexao = conectar()

    if conexao is None:
        return

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS categorias (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(100) NOT NULL UNIQUE
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS produtos (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(150) NOT NULL,
                categoria VARCHAR(100) NOT NULL,
                categoria_id INTEGER,
                quantidade INTEGER NOT NULL
                    CHECK (quantidade >= 0),
                preco NUMERIC(10, 2) NOT NULL
                    CHECK (preco >= 0)
            );
            """
        )

        cursor.execute(
            """
            ALTER TABLE produtos
            ADD COLUMN IF NOT EXISTS categoria_id INTEGER;
            """
        )

        cursor.execute(
            """
            INSERT INTO categorias (nome)
            SELECT DISTINCT categoria
            FROM produtos
            WHERE categoria IS NOT NULL
              AND TRIM(categoria) <> ''
            ON CONFLICT (nome) DO NOTHING;
            """
        )

        cursor.execute(
            """
            UPDATE produtos p
            SET categoria_id = c.id
            FROM categorias c
            WHERE p.categoria_id IS NULL
              AND p.categoria = c.nome;
            """
        )

        cursor.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'fk_produto_categoria'
                ) THEN
                    ALTER TABLE produtos
                    ADD CONSTRAINT fk_produto_categoria
                    FOREIGN KEY (categoria_id)
                    REFERENCES categorias(id);
                END IF;
            END $$;
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS movimentacoes (
                id SERIAL PRIMARY KEY,
                produto_id INTEGER NOT NULL,
                tipo VARCHAR(10) NOT NULL
                    CHECK (tipo IN ('ENTRADA', 'SAIDA')),
                quantidade INTEGER NOT NULL
                    CHECK (quantidade > 0),
                data_movimentacao TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT fk_produto
                    FOREIGN KEY (produto_id)
                    REFERENCES produtos(id)
                    ON DELETE CASCADE
            );
            """
        )

        conexao.commit()

        cursor.close()
        conexao.close()

        print("Banco de dados preparado com sucesso.")

    except psycopg2.Error as erro:
        print(f"Erro ao criar ou migrar tabelas: {erro}")

        conexao.rollback()
        conexao.close()