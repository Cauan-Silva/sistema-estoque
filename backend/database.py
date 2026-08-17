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
            CREATE TABLE IF NOT EXISTS produtos (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(150) NOT NULL,
                categoria VARCHAR(100) NOT NULL,
                quantidade INTEGER NOT NULL CHECK (quantidade >= 0),
                preco NUMERIC(10, 2) NOT NULL CHECK (preco >= 0)
            );
            """
        )

        conexao.commit()

        cursor.close()
        conexao.close()

    except psycopg2.Error as erro:
        print(f"Erro ao criar tabela: {erro}")

        if conexao:
            conexao.rollback()
            conexao.close()