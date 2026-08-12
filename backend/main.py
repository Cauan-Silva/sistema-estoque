from produto import Produto


produtos = []


def cadastrar_produto():
    print("\n--- Cadastro de Produto ---")

    nome = input("Nome do produto: ")
    categoria = input("Categoria: ")
    quantidade = int(input("Quantidade: "))
    preco = float(input("Preço: "))

    produto = Produto(nome, categoria, quantidade, preco)

    produtos.append(produto)

    print("\nProduto cadastrado com sucesso!")


def listar_produtos():
    print("\n--- Produtos cadastrados ---")

    if not produtos:
        print("Nenhum produto cadastrado.")
        return

    for produto in produtos:
        print(produto)


def main():
    while True:
        print("\n=== Sistema de Gestão de Estoque ===")
        print("1 - Cadastrar produto")
        print("2 - Listar produtos")
        print("0 - Sair")

        opcao = input("Escolha uma opção: ")

        if opcao == "1":
            cadastrar_produto()

        elif opcao == "2":
            listar_produtos()

        elif opcao == "0":
            print("Sistema encerrado.")
            break

        else:
            print("Opção inválida.")


if __name__ == "__main__":
    main()