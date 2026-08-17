from database import criar_tabela

from repositorio import (
    atualizar_produto,
    buscar_produto_por_id,
    cadastrar_produto,
    excluir_produto,
    listar_produtos
)


def cadastrar():
    print("\n--- Cadastro de Produto ---")

    nome = input("Nome do produto: ").strip()
    categoria = input("Categoria: ").strip()

    if not nome:
        print("Erro: o nome não pode ficar vazio.")
        return

    if not categoria:
        print("Erro: a categoria não pode ficar vazia.")
        return

    try:
        quantidade = int(input("Quantidade: "))
        preco = float(input("Preço: "))
    except ValueError:
        print("Erro: quantidade e preço devem ser números.")
        return

    if quantidade < 0:
        print("Erro: quantidade não pode ser negativa.")
        return

    if preco < 0:
        print("Erro: preço não pode ser negativo.")
        return

    id_produto = cadastrar_produto(
        nome,
        categoria,
        quantidade,
        preco
    )

    if id_produto is not None:
        print(
            f"\nProduto cadastrado com sucesso! "
            f"ID: {id_produto}"
        )


def listar():
    print("\n--- Produtos cadastrados ---")

    produtos = listar_produtos()

    if not produtos:
        print("Nenhum produto cadastrado.")
        return

    for produto in produtos:
        print(produto)


def editar():
    print("\n--- Editar Produto ---")

    listar()

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

    nome = novo_nome if novo_nome else produto.nome

    categoria = (
        nova_categoria
        if nova_categoria
        else produto.categoria
    )

    quantidade = produto.quantidade

    preco = produto.preco

    if nova_quantidade:
        try:
            quantidade = int(nova_quantidade)
        except ValueError:
            print("Quantidade inválida.")
            return

        if quantidade < 0:
            print("Quantidade não pode ser negativa.")
            return

    if novo_preco:
        try:
            preco = float(novo_preco)
        except ValueError:
            print("Preço inválido.")
            return

        if preco < 0:
            print("Preço não pode ser negativo.")
            return

    sucesso = atualizar_produto(
        id_produto,
        nome,
        categoria,
        quantidade,
        preco
    )

    if sucesso:
        print("\nProduto atualizado com sucesso!")
    else:
        print("\nNão foi possível atualizar o produto.")


def excluir():
    print("\n--- Excluir Produto ---")

    listar()

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
    ).strip().lower()

    if confirmacao != "s":
        print("Exclusão cancelada.")
        return

    sucesso = excluir_produto(id_produto)

    if sucesso:
        print("\nProduto excluído com sucesso!")
    else:
        print("\nNão foi possível excluir o produto.")


def main():
    criar_tabela()

    while True:
        print("\n=== Sistema de Gestão de Estoque ===")
        print("1 - Cadastrar produto")
        print("2 - Listar produtos")
        print("3 - Editar produto")
        print("4 - Excluir produto")
        print("0 - Sair")

        opcao = input("Escolha uma opção: ").strip()

        if opcao == "1":
            cadastrar()

        elif opcao == "2":
            listar()

        elif opcao == "3":
            editar()

        elif opcao == "4":
            excluir()

        elif opcao == "0":
            print("Sistema encerrado.")
            break

        else:
            print("Opção inválida.")


if __name__ == "__main__":
    main()