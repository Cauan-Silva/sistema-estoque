from datetime import datetime, timedelta, timezone

import httpx
import pytest

from backend.precos import servico
from backend.precos.autorizar_mercado_livre import extrair_codigo
from backend.precos.credenciais import salvar_credenciais
from backend.database import conectar
from backend.precos.mercado_livre import NOME_CREDENCIAL, MercadoLivre, trocar_codigo
from backend.tests.apoio_compras import compra_registrada


@pytest.fixture(autouse=True)
def sem_configuracao_oauth(monkeypatch):
    for nome in ("MERCADO_LIVRE_CLIENT_ID", "MERCADO_LIVRE_CLIENT_SECRET", "MERCADO_LIVRE_REDIRECT_URI"):
        monkeypatch.delenv(nome, raising=False)


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


# ---------- Autorização OAuth e renovação automática ----------


def configurar_oauth(monkeypatch):
    monkeypatch.delenv("MERCADO_LIVRE_TOKEN", raising=False)
    monkeypatch.setenv("MERCADO_LIVRE_CLIENT_ID", "app-123")
    monkeypatch.setenv("MERCADO_LIVRE_CLIENT_SECRET", "segredo")
    monkeypatch.setenv("MERCADO_LIVRE_REDIRECT_URI", "https://exemplo.com/retorno")


def fonte_oauth(chamadas, busca_status=(200,), token_status=200):
    respostas_busca = list(busca_status)
    contador = {"token": 0}

    def responder(requisicao):
        chamadas.append(requisicao)

        if requisicao.url.path == "/oauth/token":
            contador["token"] += 1
            if token_status >= 400:
                return httpx.Response(token_status, json={"error": "invalid_grant", "message": "invalid refresh"})
            return httpx.Response(
                200,
                json={
                    "access_token": f"novo-access-{contador['token']}",
                    "refresh_token": f"novo-refresh-{contador['token']}",
                    "expires_in": 21600,
                },
            )

        status = respostas_busca.pop(0) if len(respostas_busca) > 1 else respostas_busca[0]
        return httpx.Response(status, json=RESPOSTA_ML if status == 200 else {})

    return MercadoLivre(cliente=httpx.Client(transport=httpx.MockTransport(responder)))


def credencial_salva():
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT access_token, refresh_token FROM credenciais_externas WHERE fonte = %s;",
        (NOME_CREDENCIAL,),
    )
    registro = cursor.fetchone()
    cursor.close()
    conexao.close()
    return registro


def test_oauth_sem_autorizacao_pede_o_comando(monkeypatch):
    configurar_oauth(monkeypatch)
    chamadas = []

    resultado = fonte_oauth(chamadas).buscar("cabo")

    assert resultado.situacao == "nao_configurada"
    assert "autorizar_mercado_livre" in resultado.mensagem
    assert chamadas == []


def test_oauth_usa_token_valido_sem_renovar(monkeypatch):
    configurar_oauth(monkeypatch)
    salvar_credenciais(
        NOME_CREDENCIAL, "access-atual", "refresh-atual",
        datetime.now(timezone.utc) + timedelta(hours=3),
    )
    chamadas = []

    resultado = fonte_oauth(chamadas).buscar("cabo")

    assert resultado.situacao == "ok"
    assert [c.url.path for c in chamadas] == ["/sites/MLB/search"]
    assert chamadas[0].headers["authorization"] == "Bearer access-atual"


def test_oauth_renova_token_expirado_e_guarda_o_novo(monkeypatch):
    configurar_oauth(monkeypatch)
    salvar_credenciais(
        NOME_CREDENCIAL, "access-velho", "refresh-velho",
        datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    chamadas = []

    resultado = fonte_oauth(chamadas).buscar("cabo")

    assert resultado.situacao == "ok"
    assert [c.url.path for c in chamadas] == ["/oauth/token", "/sites/MLB/search"]

    corpo = chamadas[0].content.decode()
    assert "grant_type=refresh_token" in corpo
    assert "refresh_token=refresh-velho" in corpo
    assert "client_id=app-123" in corpo

    assert chamadas[1].headers["authorization"] == "Bearer novo-access-1"
    assert credencial_salva() == ("novo-access-1", "novo-refresh-1")


def test_oauth_renova_e_repete_quando_a_busca_responde_401(monkeypatch):
    configurar_oauth(monkeypatch)
    salvar_credenciais(
        NOME_CREDENCIAL, "access-revogado", "refresh-atual",
        datetime.now(timezone.utc) + timedelta(hours=3),
    )
    chamadas = []

    resultado = fonte_oauth(chamadas, busca_status=(401, 200)).buscar("cabo")

    assert resultado.situacao == "ok"
    assert [c.url.path for c in chamadas] == ["/sites/MLB/search", "/oauth/token", "/sites/MLB/search"]
    assert chamadas[2].headers["authorization"] == "Bearer novo-access-1"


def test_oauth_refresh_recusado_pede_nova_autorizacao(monkeypatch):
    configurar_oauth(monkeypatch)
    salvar_credenciais(
        NOME_CREDENCIAL, "access-velho", "refresh-invalido",
        datetime.now(timezone.utc) - timedelta(minutes=1),
    )

    resultado = fonte_oauth([], token_status=400).buscar("cabo")

    assert resultado.situacao == "erro"
    assert "autorizar_mercado_livre" in resultado.mensagem
    assert credencial_salva() == ("access-velho", "refresh-invalido")


def test_trocar_codigo_da_autorizacao(monkeypatch):
    configurar_oauth(monkeypatch)
    chamadas = []

    def responder(requisicao):
        chamadas.append(requisicao)
        return httpx.Response(200, json={"access_token": "a", "refresh_token": "r", "expires_in": 21600})

    access, refresh, expira = trocar_codigo(
        "TG-123", cliente=httpx.Client(transport=httpx.MockTransport(responder))
    )

    corpo = chamadas[0].content.decode()

    assert (access, refresh) == ("a", "r")
    assert expira > datetime.now(timezone.utc) + timedelta(hours=5)
    assert "grant_type=authorization_code" in corpo
    assert "code=TG-123" in corpo
    assert "redirect_uri=https%3A%2F%2Fexemplo.com%2Fretorno" in corpo


def test_extrair_codigo_do_endereco_de_retorno():
    assert extrair_codigo("https://exemplo.com/retorno?code=TG-abc&state=1") == "TG-abc"
    assert extrair_codigo("  TG-xyz  ") == "TG-xyz"
    assert extrair_codigo("https://exemplo.com/retorno") == ""
