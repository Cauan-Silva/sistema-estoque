from backend.precos.mercado_livre import MercadoLivre


FONTES = [
    MercadoLivre(),
]


def fontes_disponiveis():
    return [{"nome": fonte.nome, "configurada": fonte.configurada()} for fonte in FONTES]


def consultar_fontes(termo: str, limite: int = 10):
    return [fonte.buscar(termo, limite).para_dict() for fonte in FONTES]
