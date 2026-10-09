import logging
import os
import time

import httpx

from backend.precos.base import FontePreco, Oferta, ResultadoFonte
from backend.precos.credenciais import (
    ErroCredencial,
    existem_credenciais,
    expiracao,
    obter_token_valido,
)


logger = logging.getLogger(__name__)

URL_API = "https://api.mercadolibre.com"
URL_BUSCA = f"{URL_API}/sites/MLB/search"
URL_CATALOGO = f"{URL_API}/products/search"
PRODUTOS_CATALOGO = 5
CONDICOES = {"new": "Novo", "used": "Usado"}
URL_TOKEN = "https://api.mercadolibre.com/oauth/token"
URL_AUTORIZACAO = "https://auth.mercadolivre.com.br/authorization"
NOME_CREDENCIAL = "mercado_livre"
VALIDADE_CACHE_SEGUNDOS = 600


class ErroOAuth(Exception):
    pass


def _variavel(nome: str) -> str:
    return os.getenv(nome, "").strip()


def credenciais_do_aplicativo():
    return {
        "client_id": _variavel("MERCADO_LIVRE_CLIENT_ID"),
        "client_secret": _variavel("MERCADO_LIVRE_CLIENT_SECRET"),
        "redirect_uri": _variavel("MERCADO_LIVRE_REDIRECT_URI"),
    }


def _pedir_token(cliente: httpx.Client, dados: dict):
    try:
        resposta = cliente.post(
            URL_TOKEN,
            data=dados,
            headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
        )
    except httpx.HTTPError as erro:
        raise ErroOAuth("Não foi possível conectar ao Mercado Livre.") from erro

    if resposta.status_code >= 400:
        try:
            detalhe = resposta.json().get("message") or resposta.json().get("error")
        except ValueError:
            detalhe = resposta.text[:200]
        raise ErroOAuth(f"O Mercado Livre recusou a autorização: {detalhe}")

    corpo = resposta.json()

    return corpo["access_token"], corpo.get("refresh_token"), expiracao(corpo.get("expires_in", 21600))


def trocar_codigo(codigo: str, cliente: httpx.Client | None = None):
    """Troca o código da autorização por tokens (usado uma vez, no comando de autorização)."""
    app = credenciais_do_aplicativo()
    proprio = cliente is None
    cliente = cliente or httpx.Client(timeout=10)

    try:
        return _pedir_token(
            cliente,
            {
                "grant_type": "authorization_code",
                "client_id": app["client_id"],
                "client_secret": app["client_secret"],
                "code": codigo.strip(),
                "redirect_uri": app["redirect_uri"],
            },
        )
    finally:
        if proprio:
            cliente.close()


class MercadoLivre(FontePreco):
    nome = "Mercado Livre"

    def __init__(self, cliente: httpx.Client | None = None):
        self._cliente = cliente
        self._cache: dict[tuple[str, int], tuple[float, ResultadoFonte]] = {}

    @property
    def url(self) -> str:
        return _variavel("MERCADO_LIVRE_URL") or URL_BUSCA

    def _usa_oauth(self) -> bool:
        app = credenciais_do_aplicativo()
        return bool(app["client_id"] and app["client_secret"])

    def configurada(self) -> bool:
        if self._usa_oauth():
            return existem_credenciais(NOME_CREDENCIAL)
        return bool(_variavel("MERCADO_LIVRE_TOKEN"))

    def _renovar(self, cliente):
        app = credenciais_do_aplicativo()

        def renovar(refresh_token):
            return _pedir_token(
                cliente,
                {
                    "grant_type": "refresh_token",
                    "client_id": app["client_id"],
                    "client_secret": app["client_secret"],
                    "refresh_token": refresh_token,
                },
            )

        return renovar

    def _token(self, cliente, forcar=False) -> str:
        if not self._usa_oauth():
            return _variavel("MERCADO_LIVRE_TOKEN")

        return obter_token_valido(NOME_CREDENCIAL, self._renovar(cliente), forcar=forcar)

    def _resultado(self, situacao, termo, mensagem=None, ofertas=None):
        return ResultadoFonte(
            fonte=self.nome,
            situacao=situacao,
            mensagem=mensagem,
            termo=termo,
            ofertas=ofertas or [],
        )

    def _consultar(self, cliente, url: str, params: dict | None = None):
        """GET autenticado; renova o token e repete uma vez se a resposta for 401."""
        resposta = None

        for tentativa in range(2):
            token = self._token(cliente, forcar=tentativa > 0)
            resposta = cliente.get(url, params=params, headers={"Authorization": f"Bearer {token}"})

            if resposta.status_code != 401 or not self._usa_oauth():
                break

        return resposta

    def _mensagem_de_erro(self, resposta) -> str | None:
        if resposta.status_code == 401:
            logger.warning("Mercado Livre recusou o acesso (HTTP 401).")
            return "O Mercado Livre recusou o acesso. Confira a configuração e a autorização do aplicativo."

        if resposta.status_code == 403:
            logger.warning("Mercado Livre bloqueou a consulta (HTTP 403): %s", resposta.text[:300])
            return (
                "O Mercado Livre bloqueou a consulta de preços para este aplicativo (erro 403). "
                "Rode python -m backend.precos.diagnosticar_mercado_livre para ver o que está liberado."
            )

        if resposta.status_code == 429:
            return "Limite de consultas do Mercado Livre atingido. Tente mais tarde."

        if resposta.status_code >= 400:
            logger.warning("Mercado Livre respondeu HTTP %s.", resposta.status_code)
            return f"O Mercado Livre respondeu com erro {resposta.status_code}."

        return None

    def _menor_oferta_do_produto(self, cliente, produto) -> Oferta | None:
        produto_id = produto.get("id")
        nome = str(produto.get("name") or produto.get("title") or "").strip()
        link = produto.get("permalink") or f"https://www.mercadolivre.com.br/p/{produto_id}"

        resposta = self._consultar(cliente, f"{URL_API}/products/{produto_id}/items", {"limit": 10})

        if resposta.status_code < 400:
            try:
                anuncios = [a for a in resposta.json().get("results", []) if a.get("price") is not None]
            except ValueError:
                anuncios = []

            if anuncios:
                melhor = min(anuncios, key=lambda a: a["price"])
                return Oferta(
                    titulo=nome,
                    preco=float(melhor["price"]),
                    moeda=melhor.get("currency_id") or "BRL",
                    link=link,
                    vendedor=None,
                    condicao=CONDICOES.get(melhor.get("condition"), melhor.get("condition")),
                )

        vencedor = produto.get("buy_box_winner")
        if not vencedor:
            detalhe = self._consultar(cliente, f"{URL_API}/products/{produto_id}")
            if detalhe.status_code < 400:
                try:
                    vencedor = detalhe.json().get("buy_box_winner")
                except ValueError:
                    vencedor = None

        if vencedor and vencedor.get("price") is not None:
            return Oferta(
                titulo=nome,
                preco=float(vencedor["price"]),
                moeda=vencedor.get("currency_id") or "BRL",
                link=link,
                vendedor=None,
                condicao=CONDICOES.get(vencedor.get("condition"), vencedor.get("condition")),
            )

        return None

    def _buscar_no_catalogo(self, cliente, termo: str, limite: int):
        """Devolve (ofertas, None) ou (None, resposta_com_erro)."""
        resposta = self._consultar(
            cliente,
            URL_CATALOGO,
            {"status": "active", "site_id": "MLB", "q": termo, "limit": min(limite, 10)},
        )

        if resposta.status_code >= 400:
            return [], resposta

        try:
            produtos = resposta.json().get("results", [])
        except ValueError:
            produtos = []

        ofertas = []
        for produto in produtos[:PRODUTOS_CATALOGO]:
            oferta = self._menor_oferta_do_produto(cliente, produto)
            if oferta:
                ofertas.append(oferta)

        return ofertas, None

    def buscar(self, termo: str, limite: int = 10) -> ResultadoFonte:
        termo = termo.strip()

        if not self.configurada():
            mensagem = (
                "Autorize o aplicativo com: python -m backend.precos.autorizar_mercado_livre"
                if self._usa_oauth()
                else "Configure o Mercado Livre no .env para consultar preços de mercado."
            )
            return self._resultado("nao_configurada", termo, mensagem)

        chave = (termo.lower(), limite)
        guardado = self._cache.get(chave)

        if guardado and time.monotonic() - guardado[0] < VALIDADE_CACHE_SEGUNDOS:
            return guardado[1]

        cliente = self._cliente or httpx.Client(timeout=8)

        try:
            resposta = self._consultar(cliente, self.url, {"q": termo, "limit": limite})

            if resposta.status_code == 403:
                # Desde 2025 o Mercado Livre bloqueia a busca de anúncios para a maioria
                # dos aplicativos. A busca no catálogo de produtos costuma continuar liberada.
                logger.info("Busca de anúncios bloqueada (403); usando o catálogo de produtos.")
                ofertas, resposta = self._buscar_no_catalogo(cliente, termo, limite)
            else:
                ofertas = None

        except (ErroCredencial, ErroOAuth) as erro:
            logger.warning("Credencial do Mercado Livre indisponível: %s", erro)
            return self._resultado(
                "erro",
                termo,
                "A autorização do Mercado Livre expirou ou foi revogada. "
                "Rode de novo: python -m backend.precos.autorizar_mercado_livre",
            )

        except httpx.HTTPError as erro:
            logger.warning("Mercado Livre indisponível: %s", erro)
            return self._resultado("erro", termo, "Não foi possível conectar ao Mercado Livre.")

        finally:
            if self._cliente is None:
                cliente.close()

        if ofertas is None:
            erro = self._mensagem_de_erro(resposta)
            if erro:
                return self._resultado("erro", termo, erro)

            try:
                dados = resposta.json()
            except ValueError:
                return self._resultado("erro", termo, "Resposta inesperada do Mercado Livre.")

            ofertas = [
                Oferta(
                    titulo=str(item.get("title", "")).strip(),
                    preco=float(item["price"]),
                    moeda=item.get("currency_id") or "BRL",
                    link=item.get("permalink"),
                    vendedor=(item.get("seller") or {}).get("nickname"),
                    condicao=CONDICOES.get(item.get("condition"), item.get("condition")),
                )
                for item in dados.get("results", [])[:limite]
                if item.get("price") is not None
            ]

        elif resposta is not None:
            erro = self._mensagem_de_erro(resposta)
            if erro:
                return self._resultado("erro", termo, erro)

        resultado = self._resultado(
            "ok",
            termo,
            None if ofertas else "Nenhuma oferta encontrada para este termo.",
            ofertas,
        )

        self._cache[chave] = (time.monotonic(), resultado)

        return resultado
