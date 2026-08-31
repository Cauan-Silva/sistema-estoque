class Produto:
    def __init__(
        self,
        id,
        nome,
        categoria_id,
        categoria,
        quantidade,
        preco
    ):
        self.id = id
        self.nome = nome
        self.categoria_id = categoria_id
        self.categoria = categoria
        self.quantidade = quantidade
        self.preco = preco

    def __str__(self):
        return (
            f"ID: {self.id} | "
            f"Produto: {self.nome} | "
            f"Categoria: {self.categoria} | "
            f"Quantidade: {self.quantidade} | "
            f"Preço: R$ {self.preco:.2f}"
        )