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

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(150) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                senha_hash VARCHAR(255) NOT NULL,
                ativo BOOLEAN NOT NULL DEFAULT TRUE,
                data_criacao TIMESTAMP NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS fornecedores (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(150) NOT NULL,
                cpf_cnpj VARCHAR(20),
                contato VARCHAR(150),
                telefone VARCHAR(30),
                email VARCHAR(150),
                site VARCHAR(255),
                ativo BOOLEAN NOT NULL DEFAULT TRUE,
                data_criacao TIMESTAMP NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        cursor.execute(
            """
            ALTER TABLE produtos
            ADD COLUMN IF NOT EXISTS fornecedor_id INTEGER;
            """
        )

        cursor.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'fk_produto_fornecedor'
                ) THEN
                    ALTER TABLE produtos
                    ADD CONSTRAINT fk_produto_fornecedor
                    FOREIGN KEY (fornecedor_id)
                    REFERENCES fornecedores(id)
                    ON DELETE SET NULL;
                END IF;
            END $$;
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS solicitacoes_compra (
                id SERIAL PRIMARY KEY,
                solicitante_id INTEGER NOT NULL
                    REFERENCES usuarios(id),
                status VARCHAR(20) NOT NULL DEFAULT 'ABERTA'
                    CHECK (
                        status IN (
                            'ABERTA',
                            'EM_COTACAO',
                            'APROVADA',
                            'REPROVADA',
                            'COMPRADA',
                            'RECEBIDA',
                            'CANCELADA'
                        )
                    ),
                observacao VARCHAR(500),
                data_criacao TIMESTAMP NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                data_atualizacao TIMESTAMP NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS itens_solicitacao_compra (
                id SERIAL PRIMARY KEY,
                solicitacao_id INTEGER NOT NULL
                    REFERENCES solicitacoes_compra(id)
                    ON DELETE CASCADE,
                produto_id INTEGER NOT NULL
                    REFERENCES produtos(id),
                quantidade INTEGER NOT NULL
                    CHECK (quantidade > 0),

                CONSTRAINT uq_item_solicitacao_produto
                    UNIQUE (solicitacao_id, produto_id)
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cotacoes (
                id SERIAL PRIMARY KEY,
                solicitacao_id INTEGER NOT NULL
                    REFERENCES solicitacoes_compra(id)
                    ON DELETE CASCADE,
                fornecedor_id INTEGER NOT NULL
                    REFERENCES fornecedores(id),
                frete NUMERIC(10, 2) NOT NULL DEFAULT 0
                    CHECK (frete >= 0),
                prazo_entrega_dias INTEGER NOT NULL
                    CHECK (prazo_entrega_dias >= 0),
                validade DATE,
                observacao VARCHAR(500),
                data_criacao TIMESTAMP NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                data_atualizacao TIMESTAMP NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT uq_cotacao_solicitacao_fornecedor
                    UNIQUE (solicitacao_id, fornecedor_id)
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS itens_cotacao (
                id SERIAL PRIMARY KEY,
                cotacao_id INTEGER NOT NULL
                    REFERENCES cotacoes(id)
                    ON DELETE CASCADE,
                produto_id INTEGER NOT NULL
                    REFERENCES produtos(id),
                preco_unitario NUMERIC(10, 2) NOT NULL
                    CHECK (preco_unitario >= 0),

                CONSTRAINT uq_item_cotacao_produto
                    UNIQUE (cotacao_id, produto_id)
            );
            """
        )

        cursor.execute(
            """
            ALTER TABLE solicitacoes_compra
            ADD COLUMN IF NOT EXISTS cotacao_aprovada_id INTEGER
                REFERENCES cotacoes(id),
            ADD COLUMN IF NOT EXISTS decisao_por_id INTEGER
                REFERENCES usuarios(id),
            ADD COLUMN IF NOT EXISTS data_decisao TIMESTAMP,
            ADD COLUMN IF NOT EXISTS justificativa_decisao VARCHAR(500);
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS compras (
                id SERIAL PRIMARY KEY,
                solicitacao_id INTEGER NOT NULL UNIQUE
                    REFERENCES solicitacoes_compra(id),
                cotacao_id INTEGER NOT NULL
                    REFERENCES cotacoes(id),
                fornecedor_id INTEGER NOT NULL
                    REFERENCES fornecedores(id),
                comprador_id INTEGER NOT NULL
                    REFERENCES usuarios(id),
                numero_pedido VARCHAR(50),
                data_compra DATE NOT NULL,
                previsao_entrega DATE NOT NULL,
                valor_itens NUMERIC(12, 2) NOT NULL,
                frete NUMERIC(10, 2) NOT NULL,
                valor_total NUMERIC(12, 2) NOT NULL,
                observacao VARCHAR(500),
                data_criacao TIMESTAMP NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS itens_compra (
                id SERIAL PRIMARY KEY,
                compra_id INTEGER NOT NULL
                    REFERENCES compras(id)
                    ON DELETE CASCADE,
                produto_id INTEGER NOT NULL
                    REFERENCES produtos(id),
                quantidade INTEGER NOT NULL
                    CHECK (quantidade > 0),
                preco_unitario NUMERIC(10, 2) NOT NULL,
                subtotal NUMERIC(12, 2) NOT NULL
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS recebimentos (
                id SERIAL PRIMARY KEY,
                compra_id INTEGER NOT NULL
                    REFERENCES compras(id),
                recebedor_id INTEGER NOT NULL
                    REFERENCES usuarios(id),
                data_recebimento DATE NOT NULL,
                nota_fiscal VARCHAR(50),
                observacao VARCHAR(500),
                data_criacao TIMESTAMP NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        cursor.execute(
            """
            ALTER TABLE movimentacoes
            ADD COLUMN IF NOT EXISTS recebimento_id INTEGER
                REFERENCES recebimentos(id)
                ON DELETE SET NULL;
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS itens_recebimento (
                id SERIAL PRIMARY KEY,
                recebimento_id INTEGER NOT NULL
                    REFERENCES recebimentos(id)
                    ON DELETE CASCADE,
                produto_id INTEGER NOT NULL
                    REFERENCES produtos(id),
                quantidade INTEGER NOT NULL
                    CHECK (quantidade > 0),
                movimentacao_id INTEGER
                    REFERENCES movimentacoes(id)
                    ON DELETE SET NULL
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