class Produto:
    def __init__(self, nome, categoria, quantidade, preco):
        self.nome = nome
        self.categoria = categoria
        self.quantidade = quantidade
        self.preco = preco

    def __str__(self):
        return (
            f"Produto: {self.nome} | "
            f"Categoria: {self.categoria} | "
            f"Quantidade: {self.quantidade} | "
            f"Preço: R$ {self.preco:.2f}"
        )