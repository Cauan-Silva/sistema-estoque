import httpx
import pytest

from backend.precos import servico
from backend.precos.mercado_livre import MercadoLivre
from backend.tests.apoio_compras import compra_registrada


RESPOSTA_ML = {
    "results": [
        {
            "title": "Cabo de rede Cat6 305m",
            "price": 499.9,
            "currency_id": "BRL",
            "permalink": "https://produto.mercadolivre.com.br/MLB-1",
            "condition": "new",
            "seller": {"nickname": "LOJA_A"},
        },
        {"title": "Cabo Cat6 caixa", "price": 389.0, "currency_id": "BRL", "condition": "used"},
        {"title": "Sem preço", "price": None},
        {"title": "Cabo importado", "price": 120.0, "currency_id": "USD"},
    ]
}


def fonte_simulada(status=200, corpo=None, chamadas=None):
    def responder(requisicao):
        if chamadas is not None:
            chamadas.append(requisicao)
        return httpx.Response(status, json=corpo if corpo is not None else RESPOSTA_ML)

    return MercadoLivre(cliente=httpx.Client(transport=httpx.MockTransport(responder)))


def test_sem_token_nao_consulta(monkeypatch):
    monkeypatch.delenv("MERCADO_LIVRE_TOKEN", raising=False)
    chamadas = []

    resultado = fonte_simulada(chamadas=chamadas).buscar("cabo")

    assert resultado.situacao == "nao_configurada"
    assert chamadas == []


def test_busca_com_token(monkeypatch):
    monkeypatch.setenv("MERCADO_LIVRE_TOKEN", "token-teste")
    chamadas = []

    resultado = fonte_simulada(chamadas=chamadas).buscar("cabo cat6", limite=5).para_dict()

    assert chamadas[0].headers["authorization"] == "Bearer token-teste"
    assert chamadas[0].url.params["q"] == "cabo cat6"
    assert chamadas[0].url.params["limit"] == "5"

    assert resultado["situacao"] == "ok"
    assert [o["titulo"] for o in resultado["ofertas"]] == [
        "Cabo de rede Cat6 305m",
        "Cabo Cat6 caixa",
        "Cabo importado",
    ]
    assert resultado["ofertas"][0]["vendedor"] == "LOJA_A"
    assert resultado["ofertas"][0]["condicao"] == "Novo"
    assert resultado["resumo"] == {"menor": 389.0, "mediana": 444.45, "maior": 499.9, "quantidade": 2}


def test_resultado_fica_em_cache(monkeypatch):
    monkeypatch.setenv("MERCADO_LIVRE_TOKEN", "token-teste")
    chamadas = []
    fonte = fonte_simulada(chamadas=chamadas)

    fonte.buscar("cabo")
    fonte.buscar("CABO")

    assert len(chamadas) == 1


@pytest.mark.parametrize(
    "status, trecho",
    [(401, "recusou o acesso"), (403, "recusou o acesso"), (429, "Limite"), (500, "erro 500")],
)
def test_erros_da_api_externa(monkeypatch, status, trecho):
    monkeypatch.setenv("MERCADO_LIVRE_TOKEN", "token-teste")

    resultado = fonte_simulada(status=status, corpo={}).buscar("cabo")

    assert resultado.situacao == "erro"
    assert trecho in resultado.mensagem


def test_sem_conexao(monkeypatch):
    monkeypatch.setenv("MERCADO_LIVRE_TOKEN", "token-teste")

    def falhar(requisicao):
        raise httpx.ConnectError("sem rede")

    fonte = MercadoLivre(cliente=httpx.Client(transport=httpx.MockTransport(falhar)))

    assert fonte.buscar("cabo").situacao == "erro"


def test_consulta_de_produto_com_historico_e_fonte(cliente_autenticado, monkeypatch):
    monkeypatch.setenv("MERCADO_LIVRE_TOKEN", "token-teste")
    monkeypatch.setattr(servico, "FONTES", [fonte_simulada()])

    _, compra = compra_registrada(cliente_autenticado)
    cabo = compra["itens"][0]["produto_id"]

    resposta = cliente_autenticado.get(f"/precos/produtos/{cabo}")

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["produto"]["nome"] == "Cabo"
    assert dados["resumo"]["ultimo_pago"] == 2.5
    assert dados["resumo"]["media_paga"] == 2.5
    assert dados["resumo"]["compras"] == 1
    assert dados["compras"][0]["fornecedor"] == "Fornecedor Aprovado"
    assert dados["cotacoes"][0]["preco_unitario"] == 2.5
    assert dados["externas"][0]["fonte"] == "Mercado Livre"
    assert dados["externas"][0]["termo"] == "Cabo"
    assert dados["externas"][0]["resumo"]["quantidade"] == 2


def test_consulta_com_termo_proprio_e_sem_externas(cliente_autenticado, monkeypatch):
    monkeypatch.setenv("MERCADO_LIVRE_TOKEN", "token-teste")
    monkeypatch.setattr(servico, "FONTES", [fonte_simulada()])

    _, compra = compra_registrada(cliente_autenticado)
    cabo = compra["itens"][0]["produto_id"]

    com_termo = cliente_autenticado.get(f"/precos/produtos/{cabo}?busca=cabo%20cat6%20305m").json()
    sem_externas = cliente_autenticado.get(f"/precos/produtos/{cabo}?externas=false").json()

    assert com_termo["externas"][0]["termo"] == "cabo cat6 305m"
    assert sem_externas["externas"] == []


def test_produto_sem_historico(cliente_autenticado, monkeypatch):
    monkeypatch.delenv("MERCADO_LIVRE_TOKEN", raising=False)

    categoria = cliente_autenticado.post("/categorias", json={"nome": "Nova"}).json()
    produto = cliente_autenticado.post(
        "/produtos",
        json={"nome": "Produto Novo", "categoria_id": categoria["id"], "quantidade": 0, "preco": 7.5},
    ).json()

    dados = cliente_autenticado.get(f"/precos/produtos/{produto['id']}").json()

    assert dados["resumo"] == {
        "ultimo_pago": None,
        "menor_pago": None,
        "maior_pago": None,
        "media_paga": None,
        "compras": 0,
    }
    assert dados["produto"]["preco_cadastro"] == 7.5
    assert dados["externas"][0]["situacao"] == "nao_configurada"


def test_produto_inexistente(cliente_autenticado):
    assert cliente_autenticado.get("/precos/produtos/999999").status_code == 404


def test_fontes(cliente_autenticado, monkeypatch):
    monkeypatch.delenv("MERCADO_LIVRE_TOKEN", raising=False)

    assert cliente_autenticado.get("/precos/fontes").json() == [
        {"nome": "Mercado Livre", "configurada": False}
    ]
