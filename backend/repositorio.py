import json
import os

from produto import Produto


ARQUIVO_DADOS = os.path.join(
    os.path.dirname(__file__),
    "dados.json"
)


def carregar_produtos():
    produtos = []

    if not os.path.exists(ARQUIVO_DADOS):
        return produtos

    try:
        with open(ARQUIVO_DADOS, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)

        for item in dados:
            produto = Produto(
                item["id"],
                item["nome"],
                item["categoria"],
                item["quantidade"],
                item["preco"]
            )

            produtos.append(produto)

    except json.JSONDecodeError:
        print("Erro ao carregar o arquivo de dados.")

    return produtos


def salvar_produtos(produtos):
    dados = []

    for produto in produtos:
        dados.append(produto.para_dicionario())

    with open(ARQUIVO_DADOS, "w", encoding="utf-8") as arquivo:
        json.dump(
            dados,
            arquivo,
            indent=4,
            ensure_ascii=False
        )