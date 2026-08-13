class Produto:
    def __init__(self, id, nome, categoria, quantidade, preco):
        self.id = id
        self.nome = nome
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

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "categoria": self.categoria,
            "quantidade": self.quantidade,
            "preco": self.preco
        }