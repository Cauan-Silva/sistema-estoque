import psycopg


def conectar():
    return psycopg.connect(
        host="127.0.0.1",
        dbname="sistema_estoque",
        user="postgres",
        password="1234",
        port=5432
    )


if __name__ == "__main__":
    try:
        conexao = conectar()
        print("Conexão com PostgreSQL realizada com sucesso!")
        conexao.close()

    except Exception as erro:
        print("Erro ao conectar ao PostgreSQL:")
        print(erro)