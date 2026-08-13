import json
import os

from produto import Produto


produtos = []

ARQUIVO_DADOS = os.path.join(
    os.path.dirname(__file__),
    "dados.json"
)


def carregar_produtos():
    if not os.path.exists(ARQUIVO_DADOS):
        return

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


def salvar_produtos():
    dados = []

    for produto in produtos:
        dados.append(produto.to_dict())

    with open(ARQUIVO_DADOS, "w", encoding="utf-8") as arquivo:
        json.dump(
            dados,
            arquivo,
            ensure_ascii=False,
            indent=4
        )


def gerar_proximo_id():
    if not produtos:
        return 1

    maior_id = max(produto.id for produto in produtos)

    return maior_id + 1


def buscar_produto_por_id(id_produto):
    for produto in produtos:
        if produto.id == id_produto:
            return produto

    return None


def cadastrar_produto():
    print("\n--- Cadastro de Produto ---")

    nome = input("Nome do produto: ").strip()
    categoria = input("Categoria: ").strip()

    if not nome:
        print("Erro: o nome do produto é obrigatório.")
        return

    if not categoria:
        print("Erro: a categoria é obrigatória.")
        return

    try:
        quantidade = int(input("Quantidade: "))
        preco = float(input("Preço: "))

    except ValueError:
        print(
            "\nErro: quantidade deve ser um número inteiro "
            "e preço deve ser um número."
        )
        return

    if quantidade < 0:
        print("\nErro: a quantidade não pode ser negativa.")
        return

    if preco < 0:
        print("\nErro: o preço não pode ser negativo.")
        return

    id_produto = gerar_proximo_id()

    produto = Produto(
        id_produto,
        nome,
        categoria,
        quantidade,
        preco
    )

    produtos.append(produto)

    salvar_produtos()

    print("\nProduto cadastrado com sucesso!")


def listar_produtos():
    print("\n--- Produtos cadastrados ---")

    if not produtos:
        print("Nenhum produto cadastrado.")
        return

    for produto in produtos:
        print(produto)


def editar_produto():
    print("\n--- Editar Produto ---")

    if not produtos:
        print("Nenhum produto cadastrado.")
        return

    listar_produtos()

    try:
        id_produto = int(
            input("\nDigite o ID do produto que deseja editar: ")
        )

    except ValueError:
        print("ID inválido.")
        return

    produto = buscar_produto_por_id(id_produto)

    if produto is None:
        print("Produto não encontrado.")
        return

    print("\nDeixe em branco para manter o valor atual.")

    novo_nome = input(
        f"Nome [{produto.nome}]: "
    ).strip()

    nova_categoria = input(
        f"Categoria [{produto.categoria}]: "
    ).strip()

    nova_quantidade = input(
        f"Quantidade [{produto.quantidade}]: "
    ).strip()

    novo_preco = input(
        f"Preço [{produto.preco:.2f}]: "
    ).strip()

    if novo_nome:
        produto.nome = novo_nome

    if nova_categoria:
        produto.categoria = nova_categoria

    if nova_quantidade:
        try:
            quantidade = int(nova_quantidade)

            if quantidade < 0:
                print(
                    "Erro: a quantidade não pode ser negativa."
                )
                return

            produto.quantidade = quantidade

        except ValueError:
            print("Quantidade inválida.")
            return

    if novo_preco:
        try:
            preco = float(novo_preco)

            if preco < 0:
                print(
                    "Erro: o preço não pode ser negativo."
                )
                return

            produto.preco = preco

        except ValueError:
            print("Preço inválido.")
            return

    salvar_produtos()

    print("\nProduto atualizado com sucesso!")


def excluir_produto():
    print("\n--- Excluir Produto ---")

    if not produtos:
        print("Nenhum produto cadastrado.")
        return

    listar_produtos()

    try:
        id_produto = int(
            input("\nDigite o ID do produto que deseja excluir: ")
        )

    except ValueError:
        print("ID inválido.")
        return

    produto = buscar_produto_por_id(id_produto)

    if produto is None:
        print("Produto não encontrado.")
        return

    confirmacao = input(
        f"Tem certeza que deseja excluir "
        f"'{produto.nome}'? (s/n): "
    ).lower()

    if confirmacao == "s":
        produtos.remove(produto)

        salvar_produtos()

        print("\nProduto excluído com sucesso!")

    else:
        print("\nExclusão cancelada.")


def main():
    carregar_produtos()

    while True:
        print("\n=== Sistema de Gestão de Estoque ===")
        print("1 - Cadastrar produto")
        print("2 - Listar produtos")
        print("3 - Editar produto")
        print("4 - Excluir produto")
        print("0 - Sair")

        opcao = input("Escolha uma opção: ")

        if opcao == "1":
            cadastrar_produto()

        elif opcao == "2":
            listar_produtos()

        elif opcao == "3":
            editar_produto()

        elif opcao == "4":
            excluir_produto()

        elif opcao == "0":
            print("Sistema encerrado.")
            break

        else:
            print("Opção inválida.")


if __name__ == "__main__":
    main()